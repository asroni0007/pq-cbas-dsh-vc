#pragma once
#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"

namespace pqcbas {
class PQRSUApp : public veins::DemoBaseApplLayer {
public:
    void initialize(int stage) override;
    void finish() override;
protected:
    void onBSM(veins::DemoSafetyMessage* bsm) override;
private:
    double rsuX = 0;
    double rsuY = 0;
    double rsuRadius = 150;
    long receivedFromCoverage = 0;
    omnetpp::cOutVector networkLatencyMs;
};
}
