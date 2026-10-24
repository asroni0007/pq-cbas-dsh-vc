package pqcbas;
import org.car2x.veins.modules.application.ieee80211p.DemoBaseApplLayer;

simple PQRSUApp extends DemoBaseApplLayer
{
    parameters:
        @class(pqcbas::PQRSUApp);
        double rsuX = default(80);
        double rsuY = default(36);
        double rsuRadius = default(150);
        @display("i=block/app2");
}
