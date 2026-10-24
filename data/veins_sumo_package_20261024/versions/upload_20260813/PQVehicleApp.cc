#include "PQVehicleApp.h"
#include "PQFragmentMessage_m.h"
#include <algorithm>
#include <cmath>

using namespace veins;
using namespace omnetpp;

Define_Module(pqcbas::PQVehicleApp);

pqcbas::PQVehicleApp::~PQVehicleApp()
{
    if (logicalMessageTimer) cancelAndDelete(logicalMessageTimer);
    logicalMessageTimer = nullptr;
}

void pqcbas::PQVehicleApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        rsuX = par("rsuX").doubleValue();
        rsuY = par("rsuY").doubleValue();
        rsuRadius = par("rsuRadius").doubleValue();
        logicalPayloadBytes = par("logicalPayloadBytes").intValue();
        fragmentPayloadBytes = par("fragmentPayloadBytes").intValue();
        fragmentHeaderBytes = par("fragmentHeaderBytes").intValue();
        logicalMessageInterval = par("logicalMessageInterval").doubleValue();
        if (logicalPayloadBytes <= 0 || fragmentPayloadBytes <= 0 || fragmentHeaderBytes < 0) {
            throw cRuntimeError("Invalid logical/fragment payload parameters");
        }
        logicalMessageTimer = new cMessage("pqLogicalMessageTimer");
        scheduleAt(simTime() + uniform(0, logicalMessageInterval.dbl()), logicalMessageTimer);
    }
}

bool pqcbas::PQVehicleApp::isInCoverage() const
{
    const double dx = curPosition.x - rsuX;
    const double dy = curPosition.y - rsuY;
    return dx * dx + dy * dy <= rsuRadius * rsuRadius;
}

void pqcbas::PQVehicleApp::handleSelfMsg(cMessage* msg)
{
    if (msg == logicalMessageTimer) {
        generateLogicalMessage();
        scheduleAt(simTime() + logicalMessageInterval, logicalMessageTimer);
        return;
    }
    DemoBaseApplLayer::handleSelfMsg(msg);
}

void pqcbas::PQVehicleApp::generateLogicalMessage()
{
    const bool inCoverage = isInCoverage();
    const int fragmentCount = (logicalPayloadBytes + fragmentPayloadBytes - 1) / fragmentPayloadBytes;
    const long logicalId = nextLogicalMessageId++;
    const simtime_t createdAt = simTime();

    if (inCoverage) {
        ++generatedLogicalInCoverage;
        generatedFragmentsInCoverage += fragmentCount;
    }

    int remaining = logicalPayloadBytes;
    for (int index = 0; index < fragmentCount; ++index) {
        const int payloadBytes = std::min(fragmentPayloadBytes, remaining);
        remaining -= payloadBytes;

        auto* fragment = new PQFragmentMessage("pqFragment");
        populateWSM(fragment);
        fragment->setSenderId(getParentModule()->getId());
        fragment->setLogicalMessageId(logicalId);
        fragment->setFragmentIndex(index);
        fragment->setFragmentCount(fragmentCount);
        fragment->setFragmentPayloadBytes(payloadBytes);
        fragment->setLogicalPayloadBytes(logicalPayloadBytes);
        fragment->setGeneratedInRsuCoverage(inCoverage);
        fragment->setLogicalCreatedAt(createdAt);
        fragment->setBitLength(static_cast<int64_t>(payloadBytes + fragmentHeaderBytes) * 8);
        sendDown(fragment);
    }
}

void pqcbas::PQVehicleApp::finish()
{
    recordScalar("generatedLogicalInRsuCoverage", generatedLogicalInCoverage);
    recordScalar("generatedFragmentsInRsuCoverage", generatedFragmentsInCoverage);
    DemoBaseApplLayer::finish();
}
