//
// Generated file, do not edit! Created by opp_msgtool 6.1 from PQFragmentMessage.msg.
//

// Disable warnings about unused variables, empty switch stmts, etc:
#ifdef _MSC_VER
#  pragma warning(disable:4101)
#  pragma warning(disable:4065)
#endif

#if defined(__clang__)
#  pragma clang diagnostic ignored "-Wshadow"
#  pragma clang diagnostic ignored "-Wconversion"
#  pragma clang diagnostic ignored "-Wunused-parameter"
#  pragma clang diagnostic ignored "-Wc++98-compat"
#  pragma clang diagnostic ignored "-Wunreachable-code-break"
#  pragma clang diagnostic ignored "-Wold-style-cast"
#elif defined(__GNUC__)
#  pragma GCC diagnostic ignored "-Wshadow"
#  pragma GCC diagnostic ignored "-Wconversion"
#  pragma GCC diagnostic ignored "-Wunused-parameter"
#  pragma GCC diagnostic ignored "-Wold-style-cast"
#  pragma GCC diagnostic ignored "-Wsuggest-attribute=noreturn"
#  pragma GCC diagnostic ignored "-Wfloat-conversion"
#endif

#include <iostream>
#include <sstream>
#include <memory>
#include <type_traits>
#include "PQFragmentMessage_m.h"

namespace omnetpp {

// Template pack/unpack rules. They are declared *after* a1l type-specific pack functions for multiple reasons.
// They are in the omnetpp namespace, to allow them to be found by argument-dependent lookup via the cCommBuffer argument

// Packing/unpacking an std::vector
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::vector<T,A>& v)
{
    int n = v.size();
    doParsimPacking(buffer, n);
    for (int i = 0; i < n; i++)
        doParsimPacking(buffer, v[i]);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::vector<T,A>& v)
{
    int n;
    doParsimUnpacking(buffer, n);
    v.resize(n);
    for (int i = 0; i < n; i++)
        doParsimUnpacking(buffer, v[i]);
}

// Packing/unpacking an std::list
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::list<T,A>& l)
{
    doParsimPacking(buffer, (int)l.size());
    for (typename std::list<T,A>::const_iterator it = l.begin(); it != l.end(); ++it)
        doParsimPacking(buffer, (T&)*it);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::list<T,A>& l)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        l.push_back(T());
        doParsimUnpacking(buffer, l.back());
    }
}

// Packing/unpacking an std::set
template<typename T, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::set<T,Tr,A>& s)
{
    doParsimPacking(buffer, (int)s.size());
    for (typename std::set<T,Tr,A>::const_iterator it = s.begin(); it != s.end(); ++it)
        doParsimPacking(buffer, *it);
}

template<typename T, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::set<T,Tr,A>& s)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        T x;
        doParsimUnpacking(buffer, x);
        s.insert(x);
    }
}

// Packing/unpacking an std::map
template<typename K, typename V, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::map<K,V,Tr,A>& m)
{
    doParsimPacking(buffer, (int)m.size());
    for (typename std::map<K,V,Tr,A>::const_iterator it = m.begin(); it != m.end(); ++it) {
        doParsimPacking(buffer, it->first);
        doParsimPacking(buffer, it->second);
    }
}

template<typename K, typename V, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::map<K,V,Tr,A>& m)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        K k; V v;
        doParsimUnpacking(buffer, k);
        doParsimUnpacking(buffer, v);
        m[k] = v;
    }
}

// Default pack/unpack function for arrays
template<typename T>
void doParsimArrayPacking(omnetpp::cCommBuffer *b, const T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimPacking(b, t[i]);
}

template<typename T>
void doParsimArrayUnpacking(omnetpp::cCommBuffer *b, T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimUnpacking(b, t[i]);
}

// Default rule to prevent compiler from choosing base class' doParsimPacking() function
template<typename T>
void doParsimPacking(omnetpp::cCommBuffer *, const T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimPacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

template<typename T>
void doParsimUnpacking(omnetpp::cCommBuffer *, T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimUnpacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

}  // namespace omnetpp

namespace pqcbas {

Register_Class(PQFragmentMessage)

PQFragmentMessage::PQFragmentMessage(const char *name, short kind) : ::veins::DemoSafetyMessage(name, kind)
{
}

PQFragmentMessage::PQFragmentMessage(const PQFragmentMessage& other) : ::veins::DemoSafetyMessage(other)
{
    copy(other);
}

PQFragmentMessage::~PQFragmentMessage()
{
}

PQFragmentMessage& PQFragmentMessage::operator=(const PQFragmentMessage& other)
{
    if (this == &other) return *this;
    ::veins::DemoSafetyMessage::operator=(other);
    copy(other);
    return *this;
}

void PQFragmentMessage::copy(const PQFragmentMessage& other)
{
    this->senderId = other.senderId;
    this->logicalMessageId = other.logicalMessageId;
    this->fragmentIndex = other.fragmentIndex;
    this->fragmentCount = other.fragmentCount;
    this->fragmentPayloadBytes = other.fragmentPayloadBytes;
    this->logicalPayloadBytes = other.logicalPayloadBytes;
    this->generatedInRsuCoverage = other.generatedInRsuCoverage;
    this->logicalCreatedAt = other.logicalCreatedAt;
}

void PQFragmentMessage::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::veins::DemoSafetyMessage::parsimPack(b);
    doParsimPacking(b,this->senderId);
    doParsimPacking(b,this->logicalMessageId);
    doParsimPacking(b,this->fragmentIndex);
    doParsimPacking(b,this->fragmentCount);
    doParsimPacking(b,this->fragmentPayloadBytes);
    doParsimPacking(b,this->logicalPayloadBytes);
    doParsimPacking(b,this->generatedInRsuCoverage);
    doParsimPacking(b,this->logicalCreatedAt);
}

void PQFragmentMessage::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::veins::DemoSafetyMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->senderId);
    doParsimUnpacking(b,this->logicalMessageId);
    doParsimUnpacking(b,this->fragmentIndex);
    doParsimUnpacking(b,this->fragmentCount);
    doParsimUnpacking(b,this->fragmentPayloadBytes);
    doParsimUnpacking(b,this->logicalPayloadBytes);
    doParsimUnpacking(b,this->generatedInRsuCoverage);
    doParsimUnpacking(b,this->logicalCreatedAt);
}

long PQFragmentMessage::getSenderId() const
{
    return this->senderId;
}

void PQFragmentMessage::setSenderId(long senderId)
{
    this->senderId = senderId;
}

long PQFragmentMessage::getLogicalMessageId() const
{
    return this->logicalMessageId;
}

void PQFragmentMessage::setLogicalMessageId(long logicalMessageId)
{
    this->logicalMessageId = logicalMessageId;
}

int PQFragmentMessage::getFragmentIndex() const
{
    return this->fragmentIndex;
}

void PQFragmentMessage::setFragmentIndex(int fragmentIndex)
{
    this->fragmentIndex = fragmentIndex;
}

int PQFragmentMessage::getFragmentCount() const
{
    return this->fragmentCount;
}

void PQFragmentMessage::setFragmentCount(int fragmentCount)
{
    this->fragmentCount = fragmentCount;
}

int PQFragmentMessage::getFragmentPayloadBytes() const
{
    return this->fragmentPayloadBytes;
}

void PQFragmentMessage::setFragmentPayloadBytes(int fragmentPayloadBytes)
{
    this->fragmentPayloadBytes = fragmentPayloadBytes;
}

int PQFragmentMessage::getLogicalPayloadBytes() const
{
    return this->logicalPayloadBytes;
}

void PQFragmentMessage::setLogicalPayloadBytes(int logicalPayloadBytes)
{
    this->logicalPayloadBytes = logicalPayloadBytes;
}

bool PQFragmentMessage::getGeneratedInRsuCoverage() const
{
    return this->generatedInRsuCoverage;
}

void PQFragmentMessage::setGeneratedInRsuCoverage(bool generatedInRsuCoverage)
{
    this->generatedInRsuCoverage = generatedInRsuCoverage;
}

::omnetpp::simtime_t PQFragmentMessage::getLogicalCreatedAt() const
{
    return this->logicalCreatedAt;
}

void PQFragmentMessage::setLogicalCreatedAt(::omnetpp::simtime_t logicalCreatedAt)
{
    this->logicalCreatedAt = logicalCreatedAt;
}

class PQFragmentMessageDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_senderId,
        FIELD_logicalMessageId,
        FIELD_fragmentIndex,
        FIELD_fragmentCount,
        FIELD_fragmentPayloadBytes,
        FIELD_logicalPayloadBytes,
        FIELD_generatedInRsuCoverage,
        FIELD_logicalCreatedAt,
    };
  public:
    PQFragmentMessageDescriptor();
    virtual ~PQFragmentMessageDescriptor();

    virtual bool doesSupport(omnetpp::cObject *obj) const override;
    virtual const char **getPropertyNames() const override;
    virtual const char *getProperty(const char *propertyName) const override;
    virtual int getFieldCount() const override;
    virtual const char *getFieldName(int field) const override;
    virtual int findField(const char *fieldName) const override;
    virtual unsigned int getFieldTypeFlags(int field) const override;
    virtual const char *getFieldTypeString(int field) const override;
    virtual const char **getFieldPropertyNames(int field) const override;
    virtual const char *getFieldProperty(int field, const char *propertyName) const override;
    virtual int getFieldArraySize(omnetpp::any_ptr object, int field) const override;
    virtual void setFieldArraySize(omnetpp::any_ptr object, int field, int size) const override;

    virtual const char *getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const override;
    virtual std::string getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const override;
    virtual omnetpp::cValue getFieldValue(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const override;

    virtual const char *getFieldStructName(int field) const override;
    virtual omnetpp::any_ptr getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const override;
};

Register_ClassDescriptor(PQFragmentMessageDescriptor)

PQFragmentMessageDescriptor::PQFragmentMessageDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(pqcbas::PQFragmentMessage)), "veins::DemoSafetyMessage")
{
    propertyNames = nullptr;
}

PQFragmentMessageDescriptor::~PQFragmentMessageDescriptor()
{
    delete[] propertyNames;
}

bool PQFragmentMessageDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<PQFragmentMessage *>(obj)!=nullptr;
}

const char **PQFragmentMessageDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = {  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *PQFragmentMessageDescriptor::getProperty(const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int PQFragmentMessageDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 8+base->getFieldCount() : 8;
}

unsigned int PQFragmentMessageDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_senderId
        FD_ISEDITABLE,    // FIELD_logicalMessageId
        FD_ISEDITABLE,    // FIELD_fragmentIndex
        FD_ISEDITABLE,    // FIELD_fragmentCount
        FD_ISEDITABLE,    // FIELD_fragmentPayloadBytes
        FD_ISEDITABLE,    // FIELD_logicalPayloadBytes
        FD_ISEDITABLE,    // FIELD_generatedInRsuCoverage
        FD_ISEDITABLE,    // FIELD_logicalCreatedAt
    };
    return (field >= 0 && field < 8) ? fieldTypeFlags[field] : 0;
}

const char *PQFragmentMessageDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "senderId",
        "logicalMessageId",
        "fragmentIndex",
        "fragmentCount",
        "fragmentPayloadBytes",
        "logicalPayloadBytes",
        "generatedInRsuCoverage",
        "logicalCreatedAt",
    };
    return (field >= 0 && field < 8) ? fieldNames[field] : nullptr;
}

int PQFragmentMessageDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "senderId") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "logicalMessageId") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "fragmentIndex") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "fragmentCount") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "fragmentPayloadBytes") == 0) return baseIndex + 4;
    if (strcmp(fieldName, "logicalPayloadBytes") == 0) return baseIndex + 5;
    if (strcmp(fieldName, "generatedInRsuCoverage") == 0) return baseIndex + 6;
    if (strcmp(fieldName, "logicalCreatedAt") == 0) return baseIndex + 7;
    return base ? base->findField(fieldName) : -1;
}

const char *PQFragmentMessageDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "long",    // FIELD_senderId
        "long",    // FIELD_logicalMessageId
        "int",    // FIELD_fragmentIndex
        "int",    // FIELD_fragmentCount
        "int",    // FIELD_fragmentPayloadBytes
        "int",    // FIELD_logicalPayloadBytes
        "bool",    // FIELD_generatedInRsuCoverage
        "omnetpp::simtime_t",    // FIELD_logicalCreatedAt
    };
    return (field >= 0 && field < 8) ? fieldTypeStrings[field] : nullptr;
}

const char **PQFragmentMessageDescriptor::getFieldPropertyNames(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldPropertyNames(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

const char *PQFragmentMessageDescriptor::getFieldProperty(int field, const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldProperty(field, propertyName);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

int PQFragmentMessageDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        default: return 0;
    }
}

void PQFragmentMessageDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'PQFragmentMessage'", field);
    }
}

const char *PQFragmentMessageDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string PQFragmentMessageDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        case FIELD_senderId: return long2string(pp->getSenderId());
        case FIELD_logicalMessageId: return long2string(pp->getLogicalMessageId());
        case FIELD_fragmentIndex: return long2string(pp->getFragmentIndex());
        case FIELD_fragmentCount: return long2string(pp->getFragmentCount());
        case FIELD_fragmentPayloadBytes: return long2string(pp->getFragmentPayloadBytes());
        case FIELD_logicalPayloadBytes: return long2string(pp->getLogicalPayloadBytes());
        case FIELD_generatedInRsuCoverage: return bool2string(pp->getGeneratedInRsuCoverage());
        case FIELD_logicalCreatedAt: return simtime2string(pp->getLogicalCreatedAt());
        default: return "";
    }
}

void PQFragmentMessageDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        case FIELD_senderId: pp->setSenderId(string2long(value)); break;
        case FIELD_logicalMessageId: pp->setLogicalMessageId(string2long(value)); break;
        case FIELD_fragmentIndex: pp->setFragmentIndex(string2long(value)); break;
        case FIELD_fragmentCount: pp->setFragmentCount(string2long(value)); break;
        case FIELD_fragmentPayloadBytes: pp->setFragmentPayloadBytes(string2long(value)); break;
        case FIELD_logicalPayloadBytes: pp->setLogicalPayloadBytes(string2long(value)); break;
        case FIELD_generatedInRsuCoverage: pp->setGeneratedInRsuCoverage(string2bool(value)); break;
        case FIELD_logicalCreatedAt: pp->setLogicalCreatedAt(string2simtime(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'PQFragmentMessage'", field);
    }
}

omnetpp::cValue PQFragmentMessageDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        case FIELD_senderId: return (omnetpp::intval_t)(pp->getSenderId());
        case FIELD_logicalMessageId: return (omnetpp::intval_t)(pp->getLogicalMessageId());
        case FIELD_fragmentIndex: return pp->getFragmentIndex();
        case FIELD_fragmentCount: return pp->getFragmentCount();
        case FIELD_fragmentPayloadBytes: return pp->getFragmentPayloadBytes();
        case FIELD_logicalPayloadBytes: return pp->getLogicalPayloadBytes();
        case FIELD_generatedInRsuCoverage: return pp->getGeneratedInRsuCoverage();
        case FIELD_logicalCreatedAt: return pp->getLogicalCreatedAt().dbl();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'PQFragmentMessage' as cValue -- field index out of range?", field);
    }
}

void PQFragmentMessageDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        case FIELD_senderId: pp->setSenderId(omnetpp::checked_int_cast<long>(value.intValue())); break;
        case FIELD_logicalMessageId: pp->setLogicalMessageId(omnetpp::checked_int_cast<long>(value.intValue())); break;
        case FIELD_fragmentIndex: pp->setFragmentIndex(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_fragmentCount: pp->setFragmentCount(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_fragmentPayloadBytes: pp->setFragmentPayloadBytes(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_logicalPayloadBytes: pp->setLogicalPayloadBytes(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_generatedInRsuCoverage: pp->setGeneratedInRsuCoverage(value.boolValue()); break;
        case FIELD_logicalCreatedAt: pp->setLogicalCreatedAt(value.doubleValue()); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'PQFragmentMessage'", field);
    }
}

const char *PQFragmentMessageDescriptor::getFieldStructName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructName(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    };
}

omnetpp::any_ptr PQFragmentMessageDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void PQFragmentMessageDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    PQFragmentMessage *pp = omnetpp::fromAnyPtr<PQFragmentMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'PQFragmentMessage'", field);
    }
}

}  // namespace pqcbas

namespace omnetpp {

}  // namespace omnetpp

