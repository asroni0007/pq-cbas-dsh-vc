#include "PQRSUApp.h"
#include <cmath>

using namespace veins;
using namespace omnetpp;

Define_Module(pqcbas::PQRSUApp);

void pqcbas::PQRSUApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        rsuX = par("rsuX").doubleValue();
        rsuY = par("rsuY").doubleValue();
        rsuRadius = par("rsuRadius").doubleValue();
        networkLatencyMs.setName("pqNetworkLatencyMs");
    }
}

void pqcbas::PQRSUApp::onBSM(DemoSafetyMessage* bsm)
{
    const auto p = bsm->getSenderPos();
    const double dx = p.x - rsuX;
    const double dy = p.y - rsuY;
    if (dx * dx + dy * dy > rsuRadius * rsuRadius) return;

    ++receivedFromCoverage;
    const double delayMs = (simTime() - bsm->getCreationTime()).dbl() * 1000.0;
    networkLatencyMs.record(delayMs);
}

void pqcbas::PQRSUApp::finish()
{
    recordScalar("receivedFromRsuCoverage", receivedFromCoverage);
    DemoBaseApplLayer::finish();
}
