# CATE Extension for ATNA

To include IHE ATNA audit events in a CATE trace, add `patient_id_hash` and `provider_id_hash` to ATNA messages when they occur during an active CATE session. The platform correlates by matching these hashes to CATE events.

## DICOM / RFC 3881 XML

Add a custom element to the AuditMessage:

```xml
<AuditMessage>
  <!-- standard ATNA elements: EventIdentification, ActiveParticipant, etc. -->
  <CATE>
    <PatientIDHash>a1b2c3d4e5f6...</PatientIDHash>
    <ProviderIDHash>d4e5f6789012...</ProviderIDHash>
  </CATE>
</AuditMessage>
```

## FHIR AuditEvent (BALP)

Add extensions:

```json
{
  "resourceType": "AuditEvent",
  "extension": [
    {
      "url": "https://cate-spec.org/StructureDefinition/patient-id-hash",
      "valueString": "a1b2c3d4e5f6..."
    },
    {
      "url": "https://cate-spec.org/StructureDefinition/provider-id-hash",
      "valueString": "d4e5f6789012..."
    }
  ]
}
```

## Hospital Responsibility

When emitting ATNA events for actions during an active session (e.g., provider opened chart, viewed labs), include `patient_id_hash` and `provider_id_hash` in the ATNA message via the CATE extension. The platform can then aggregate ATNA events with CATE events by matching these hashes to build a unified timeline.
