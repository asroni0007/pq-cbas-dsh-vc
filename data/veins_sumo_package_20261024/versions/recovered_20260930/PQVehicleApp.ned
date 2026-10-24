package pqcbas;
import org.car2x.veins.modules.application.ieee80211p.DemoBaseApplLayer;

simple PQVehicleApp extends DemoBaseApplLayer
{
    parameters:
        @class(pqcbas::PQVehicleApp);
        double rsuX = default(80);
        double rsuY = default(36);
        double rsuRadius = default(150);
        int logicalPayloadBytes = default(3465);
        int fragmentPayloadBytes = default(1200);
        int fragmentHeaderBytes = default(48);
        double logicalMessageInterval @unit(s) = default(0.1s);
        @display("i=block/app2");
}
