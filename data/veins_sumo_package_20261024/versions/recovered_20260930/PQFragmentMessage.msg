import veins.modules.messages.DemoSafetyMessage;
import veins.base.utils.SimpleAddress;
cplusplus {{
#include "veins/modules/messages/DemoSafetyMessage_m.h"
}}

namespace pqcbas;

packet PQFragmentMessage extends veins::DemoSafetyMessage
{
    veins::LAddress::L2Type senderAddress = -1;
    long logicalMessageId;
    int fragmentIndex;
    int fragmentCount;
    int fragmentPayloadBytes;
    int logicalPayloadBytes;
    bool generatedInRsuCoverage;
    simtime_t logicalCreatedAt;
}
