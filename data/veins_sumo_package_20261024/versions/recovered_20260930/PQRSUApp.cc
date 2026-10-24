#include "PQRSUApp.h"
#include "PQFragmentMessage_m.h"
#include <cmath>

using namespace veins;
using namespace omnetpp;

Define_Module(pqcbas::PQRSUApp);

pqcbas::PQRSUApp::~PQRSUApp()
{
    if (cleanupTimer) cancelAndDelete(cleanupTimer);
    cleanupTimer = nullptr;
}

void pqcbas::PQRSUApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        rsuX = par("rsuX").doubleValue();
        rsuY = par("rsuY").doubleValue();
        rsuRadius = par("rsuRadius").doubleValue();
        logicalDeadline = par("logicalDeadline").doubleValue();
        reassemblyTimeout = par("reassemblyTimeout").doubleValue();
        cleanupInterval = par("cleanupInterval").doubleValue();
        if (logicalDeadline <= SIMTIME_ZERO || reassemblyTimeout < logicalDeadline || cleanupInterval <= SIMTIME_ZERO) {
            throw cRuntimeError("Require 0 < logicalDeadline <= reassemblyTimeout and cleanupInterval > 0");
        }
        fragmentLatencyMs.setName("pqFragmentLatencyMs");
        logicalCompletionLatencyMs.setName("pqLogicalCompletionLatencyMs");
        cleanupTimer = new cMessage("pqReassemblyCleanupTimer");
        scheduleAt(simTime() + cleanupInterval, cleanupTimer);
    }
}

void pqcbas::PQRSUApp::onBSM(DemoSafetyMessage* bsm)
{
    auto* fragment = dynamic_cast<PQFragmentMessage*>(bsm);
    if (!fragment) return;
    if (!fragment->getGeneratedInRsuCoverage()) return;

    const int index = fragment->getFragmentIndex();
    const int count = fragment->getFragmentCount();
    if (count <= 0 || index < 0 || index >= count || fragment->getLogicalPayloadBytes() <= 0) {
        ++malformedFragments;
        return;
    }

    ++receivedFragmentsInCoverage;
    fragmentLatencyMs.record((simTime() - fragment->getLogicalCreatedAt()).dbl() * 1000.0);

    const ReassemblyKey key(fragment->getSenderAddress(), fragment->getLogicalMessageId());
    auto [it, inserted] = reassembly.emplace(key, ReassemblyState{});
    auto& state = it->second;
    if (inserted) {
        state.expectedFragments = count;
        state.logicalPayloadBytes = fragment->getLogicalPayloadBytes();
        state.logicalCreatedAt = fragment->getLogicalCreatedAt();
        state.received.assign(count, false);
    }
    else if (state.expectedFragments != count || state.logicalPayloadBytes != fragment->getLogicalPayloadBytes()) {
        ++malformedFragments;
        return;
    }

    if (state.received[index]) {
        ++duplicateFragments;
        return;
    }
    state.received[index] = true;
    ++state.receivedFragments;

    if (state.receivedFragments == state.expectedFragments) {
        const simtime_t latency = simTime() - state.logicalCreatedAt;
        ++completedLogicalMessages;
        logicalCompletionLatencyMs.record(latency.dbl() * 1000.0);
        if (latency <= logicalDeadline) ++completedBeforeDeadline;
        else ++completedAfterDeadline;
        reassembly.erase(it);
    }
}

void pqcbas::PQRSUApp::handleSelfMsg(cMessage* msg)
{
    if (msg == cleanupTimer) {
        expireReassemblies();
        scheduleAt(simTime() + cleanupInterval, cleanupTimer);
        return;
    }
    DemoBaseApplLayer::handleSelfMsg(msg);
}

void pqcbas::PQRSUApp::expireReassemblies(bool finalSweep)
{
    for (auto it = reassembly.begin(); it != reassembly.end();) {
        const bool expired = finalSweep || simTime() - it->second.logicalCreatedAt > reassemblyTimeout;
        if (expired) {
            ++reassemblyTimeouts;
            it = reassembly.erase(it);
        }
        else ++it;
    }
}

void pqcbas::PQRSUApp::finish()
{
    expireReassemblies(true);
    recordScalar("receivedFragmentsInRsuCoverage", receivedFragmentsInCoverage);
    recordScalar("duplicateFragments", duplicateFragments);
    recordScalar("malformedFragments", malformedFragments);
    recordScalar("completedLogicalMessages", completedLogicalMessages);
    recordScalar("completedBeforeDeadline", completedBeforeDeadline);
    recordScalar("completedAfterDeadline", completedAfterDeadline);
    recordScalar("reassemblyTimeouts", reassemblyTimeouts);
    DemoBaseApplLayer::finish();
}
