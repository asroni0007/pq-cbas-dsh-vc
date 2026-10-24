package pqcbas;
import org.car2x.veins.nodes.RSU;
import org.car2x.veins.nodes.Scenario;

network PQScenario extends Scenario
{
    submodules:
        rsu[1]: RSU {
            @display("p=80,36;i=veins/sign/yellowdiamond;is=vs");
        }
}
