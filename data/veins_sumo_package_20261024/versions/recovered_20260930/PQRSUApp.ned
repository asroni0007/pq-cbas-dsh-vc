package pqcbas;
import org.car2x.veins.modules.application.ieee80211p.DemoBaseApplLayer;

simple PQRSUApp extends DemoBaseApplLayer
{
    parameters:
        @class(pqcbas::PQRSUApp);
        double rsuX = default(80);
        double rsuY = default(36);
        double rsuRadius = default(150);
        double logicalDeadline @unit(s) = default(0.1s);
        double reassemblyTimeout @unit(s) = default(0.5s);
        double cleanupInterval @unit(s) = default(0.01s);
        @display("i=block/app2");
}
