#include "PQVehicleApp.h"
#include <cmath>

using namespace veins;
using namespace omnetpp;

Define_Module(pqcbas::PQVehicleApp);

void pqcbas::PQVehicleApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        rsuX = par("rsuX").doubleValue();
        rsuY = par("rsuY").doubleValue();
        rsuRadius = par("rsuRadius").doubleValue();
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
    if (msg && msg->getKind() == SEND_BEACON_EVT && isInCoverage()) {
        ++generatedInCoverage;
    }
    DemoBaseApplLayer::handleSelfMsg(msg);
}

void pqcbas::PQVehicleApp::finish()
{
    recordScalar("generatedInRsuCoverage", generatedInCoverage);
    DemoBaseApplLayer::finish();
}
