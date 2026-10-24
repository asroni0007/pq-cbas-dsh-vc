#pragma once
#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"

namespace pqcbas {
class PQVehicleApp : public veins::DemoBaseApplLayer {
public:
    void initialize(int stage) override;
    void finish() override;
protected:
    void handleSelfMsg(omnetpp::cMessage* msg) override;
private:
    double rsuX = 0;
    double rsuY = 0;
    double rsuRadius = 150;
    long generatedInCoverage = 0;
    bool isInCoverage() const;
};
}
