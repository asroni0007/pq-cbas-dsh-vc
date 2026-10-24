#pragma once
#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"

namespace pqcbas {
class PQVehicleApp : public veins::DemoBaseApplLayer {
public:
    ~PQVehicleApp() override;
    void initialize(int stage) override;
    void finish() override;
protected:
    void handleSelfMsg(omnetpp::cMessage* msg) override;
private:
    double rsuX = 0;
    double rsuY = 0;
    double rsuRadius = 150;
    int logicalPayloadBytes = 0;
    int fragmentPayloadBytes = 1200;
    int fragmentHeaderBytes = 48;
    omnetpp::simtime_t logicalMessageInterval = 0.1;
    omnetpp::cMessage* logicalMessageTimer = nullptr;
    long nextLogicalMessageId = 0;
    long generatedLogicalInCoverage = 0;
    long generatedFragmentsInCoverage = 0;
    bool isInCoverage() const;
    void generateLogicalMessage();
};
}
