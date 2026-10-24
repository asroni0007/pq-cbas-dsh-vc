import veins.modules.messages.DemoSafetyMessage;

cplusplus {{
#include "veins/modules/messages/DemoSafetyMessage_m.h"
}}

namespace pqcbas;

packet PQFragmentMessage extends veins::DemoSafetyMessage
{
    long senderId;
    long logicalMessageId;
    int fragmentIndex;
    int fragmentCount;
    int fragmentPayloadBytes;
    int logicalPayloadBytes;
    bool generatedInRsuCoverage;
    simtime_t logicalCreatedAt;
}
