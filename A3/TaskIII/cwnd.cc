#include <fstream>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"

using namespace ns3;
using namespace std;
int drop = 0;
int Max_window = 0;


class MyApp : public Application
{
public:
  MyApp ();
  virtual ~MyApp ();

  /**
   * Register this type.
   * \return The TypeId.
   */
  static TypeId GetTypeId (void);
  void Setup (Ptr<Socket> socket, Address address, uint32_t packetSize, uint32_t nPackets, DataRate dataRate);
  void ChangeRate(DataRate rate);
private:
  virtual void StartApplication (void);
  virtual void StopApplication (void);

  void ScheduleTx (void);
  void SendPacket (void);
  

  Ptr<Socket>     m_socket;
  Address         m_peer;
  uint32_t        m_packetSize;
  uint32_t        m_nPackets;
  DataRate        m_dataRate;
  EventId         m_sendEvent;
  bool            m_running;
  uint32_t        m_packetsSent;
};

MyApp::MyApp ()
  : m_socket (0),
    m_peer (),
    m_packetSize (0),
    m_nPackets (0),
    m_dataRate (0),
    m_sendEvent (),
    m_running (false),
    m_packetsSent (0)
{
}

MyApp::~MyApp ()
{
  m_socket = 0;
}

/* static */
TypeId MyApp::GetTypeId (void)
{
  static TypeId tid = TypeId ("MyApp")
    .SetParent<Application> ()
    .SetGroupName ("Tutorial")
    .AddConstructor<MyApp> ()
    ;
  return tid;
}

void
MyApp::Setup (Ptr<Socket> socket, Address address, uint32_t packetSize, uint32_t nPackets, DataRate dataRate)
{
  m_socket = socket;
  m_peer = address;
  m_packetSize = packetSize;
  m_nPackets = nPackets;
  m_dataRate = dataRate;
}

void
MyApp::StartApplication (void)
{
  m_running = true;
  m_packetsSent = 0;
  m_socket->Bind ();
  m_socket->Connect (m_peer);
  SendPacket ();
}

void
MyApp::StopApplication (void)
{
  m_running = false;

  if (m_sendEvent.IsRunning ())
    {
      Simulator::Cancel (m_sendEvent);
    }

  if (m_socket)
    {
      m_socket->Close ();
    }
}

void
MyApp::SendPacket (void)
{
  Ptr<Packet> packet = Create<Packet> (m_packetSize);
  m_socket->Send (packet);

  if (++m_packetsSent < m_nPackets)
    {
      ScheduleTx ();
    }
}

void
MyApp::ScheduleTx (void)
{
  if (m_running)
    {
      Time tNext (Seconds (m_packetSize * 8 / static_cast<double> (m_dataRate.GetBitRate ())));
      m_sendEvent = Simulator::Schedule (tNext, &MyApp::SendPacket, this);
    }
}
void
MyApp::ChangeRate (DataRate rate)
{
    m_dataRate = rate;
    return;
}
static void
CwndChange (Ptr<OutputStreamWrapper> stream, uint32_t oldCwnd, uint32_t newCwnd)
{
  NS_LOG_UNCOND (Simulator::Now ().GetSeconds () << "\t" << newCwnd);
  *stream->GetStream () << Simulator::Now ().GetSeconds () << "\t" << oldCwnd << "\t" << newCwnd << std::endl;
  Max_window = max(Max_window,(int)newCwnd);
}

static void
RxDrop (Ptr<PcapFileWrapper> file, Ptr<const Packet> p)
{
  NS_LOG_UNCOND ("RxDrop at " << Simulator::Now ().GetSeconds ());
  file->Write (Simulator::Now (), p);
  drop++;
}
static void
ChangeConfig (Ptr<MyApp> app, DataRate rate)
{
    app->ChangeRate(rate);
    return;
}
int main (int argc, char *argv[])
{
  CommandLine cmd;
  string algorithm = "Vegas";
  string appRate = "2";
  string channelRate = "5";
  cmd.AddValue("algorithm", "Congestion control algorithm", algorithm);
  cmd.AddValue("appRate", "Application data rate", appRate);
  cmd.AddValue("channelRate", "Channel data rate", channelRate);
  cmd.Parse (argc, argv);
  appRate+="Mbps";
  channelRate+="Mbps";
  cmd.Parse (argc, argv);
  NodeContainer nodes;
  nodes.Create (5);

  PointToPointHelper pointToPoint;

  pointToPoint.SetDeviceAttribute ("DataRate", StringValue ("500Kbps")); /*changed it to 500Kbps*/
  pointToPoint.SetChannelAttribute ("Delay", StringValue ("2ms")); /*changed it to 2ms*/

  NetDeviceContainer devices12,devices23,devices34,devices35;
  devices12 = pointToPoint.Install (nodes.Get(0),nodes.Get(1));
  devices23 = pointToPoint.Install (nodes.Get(1),nodes.Get(2));
  devices34 = pointToPoint.Install (nodes.Get(2),nodes.Get(3));
  devices35 = pointToPoint.Install (nodes.Get(2),nodes.Get(4));

  InternetStackHelper stack;
  stack.Install (nodes);

  Ipv4AddressHelper address;
  address.SetBase ("10.1.1.0", "255.255.255.252");
  Ipv4InterfaceContainer interfaces12 = address.Assign (devices12);

  address.SetBase ("10.1.2.0", "255.255.255.252");
  Ipv4InterfaceContainer interfaces23 = address.Assign (devices23);

  address.SetBase ("10.1.3.0", "255.255.255.252");
  Ipv4InterfaceContainer interfaces34 = address.Assign (devices34);

  address.SetBase ("10.1.4.0", "255.255.255.252");
  Ipv4InterfaceContainer interfaces35 = address.Assign (devices35);

  /*This step is very important*/
  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();


  uint16_t sinkPort1 = 8080;
  Address sinkAddress1 (InetSocketAddress (interfaces34.GetAddress (1), sinkPort1));
  PacketSinkHelper packetSinkHelper1 ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), sinkPort1));
  ApplicationContainer sinkApps1 = packetSinkHelper1.Install (nodes.Get (3));
  sinkApps1.Start (Seconds (0.));  /*make sure sink starts before the source*/
  sinkApps1.Stop (Seconds (100.));

  TypeId tid = TypeId::LookupByName ("ns3::Tcp" + algorithm);
  Config::Set ("/NodeList/*/$ns3::TcpL4Protocol/SocketType", TypeIdValue (tid));
  
  Ptr<Socket> ns3TcpSocket = Socket::CreateSocket (nodes.Get (0), TcpSocketFactory::GetTypeId ());

  Ptr<MyApp> app1 = CreateObject<MyApp> ();
  app1->Setup (ns3TcpSocket, sinkAddress1, 1040, 100000, DataRate ("250Kbps")); 
  nodes.Get (0)->AddApplication (app1);
  app1->SetStartTime (Seconds (1.));
  app1->SetStopTime (Seconds (100.));


  uint16_t sink2Port = 9;
  Address sinkAddress2 (InetSocketAddress (interfaces35.GetAddress (1), sink2Port));
  PacketSinkHelper packetSinkHelper2 ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), sink2Port));
  ApplicationContainer sink2Apps = packetSinkHelper2.Install (nodes.Get (1));
  sink2Apps.Start (Seconds (0.));  /*make sure sink starts before the source*/
  sink2Apps.Stop (Seconds (100.));

  Ptr<Socket> ns3UdpSocket = Socket::CreateSocket (nodes.Get (1), UdpSocketFactory::GetTypeId ());

  Ptr<MyApp> app2 = CreateObject<MyApp> ();
  app2->Setup (ns3UdpSocket, sinkAddress2, 1040, 100000, DataRate ("250Kbps")); 
  nodes.Get (1)->AddApplication (app2);
  app2->SetStartTime (Seconds (20.));
  app2->SetStopTime (Seconds (100.));

  /*Schedule methods which allow you to schedule an event in the future 
  by providing the delay between the current simulation time and the 
  expiration date of the target event.*/
  Simulator::Schedule (Seconds(30.0), &ChangeConfig, app2, DataRate("500kbps"));

  
  AsciiTraceHelper asciiTraceHelper;
  Ptr<OutputStreamWrapper> stream = asciiTraceHelper.CreateFileStream ("scratch/data.cwnd");
  ns3TcpSocket->TraceConnectWithoutContext ("CongestionWindow", MakeBoundCallback (&CwndChange, stream));

  PcapHelper pcapHelper;
  Ptr<PcapFileWrapper> file = pcapHelper.CreateFile ("scratch/data.pcap", std::ios::out, PcapHelper::DLT_PPP);
  devices34.Get (1)->TraceConnectWithoutContext ("PhyRxDrop", MakeBoundCallback (&RxDrop, file));

  Simulator::Stop (Seconds (100));
  pointToPoint.EnablePcapAll ("scratch/PCAP");
  Simulator::Run ();
  Simulator::Destroy ();
  cout<<"Max_congestion_window : "<<Max_window<<" for "<<algorithm<<"\n";
  cout<<"Total number of packets dropped: "<<drop<<" for "<<algorithm<<"\n";

  return 0;
}

