#pragma once
#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include <map>
#include <utility>
#include <vector>

namespace pqcbas {
class PQRSUApp : public veins::DemoBaseApplLayer {
public:
    ~PQRSUApp() override;
    void initialize(int stage) override;
    void finish() override;
protected:
    void onBSM(veins::DemoSafetyMessage* bsm) override;
    void handleSelfMsg(omnetpp::cMessage* msg) override;
private:
    struct ReassemblyState {
        int expectedFragments = 0;
        int receivedFragments = 0;
        int logicalPayloadBytes = 0;
        omnetpp::simtime_t logicalCreatedAt;
        std::vector<bool> received;
    };
    using ReassemblyKey = std::pair<long, long>;
    double rsuX = 0;
    double rsuY = 0;
    double rsuRadius = 150;
    omnetpp::simtime_t logicalDeadline = 0.1;
    omnetpp::simtime_t reassemblyTimeout = 0.5;
    omnetpp::simtime_t cleanupInterval = 0.01;
    omnetpp::cMessage* cleanupTimer = nullptr;
    std::map<ReassemblyKey, ReassemblyState> reassembly;
    long receivedFragmentsInCoverage = 0;
    long duplicateFragments = 0;
    long malformedFragments = 0;
    long completedLogicalMessages = 0;
    long completedBeforeDeadline = 0;
    long completedAfterDeadline = 0;
    long reassemblyTimeouts = 0;
    omnetpp::cOutVector fragmentLatencyMs;
    omnetpp::cOutVector logicalCompletionLatencyMs;
    void expireReassemblies(bool finalSweep = false);
};
}
