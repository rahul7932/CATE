# CATE Extension for ATNA

To include IHE ATNA audit events in a CATE trace, add the `trace_id` to ATNA messages when they occur during an active CATE session.

## DICOM / RFC 3881 XML

Add a custom element to the AuditMessage:

```xml
<AuditMessage>
  <!-- standard ATNA elements: EventIdentification, ActiveParticipant, etc. -->
  <CATE>
    <TraceID>tr_550e8400e29b</TraceID>
  </CATE>
</AuditMessage>
```

## FHIR AuditEvent (BALP)

Add an extension:

```json
{
  "resourceType": "AuditEvent",
  "extension": [
    {
      "url": "https://cate-spec.org/StructureDefinition/trace-id",
      "valueString": "tr_550e8400e29b"
    }
  ]
}
```

## Hospital Responsibility

When emitting ATNA events for actions during an active session (e.g., provider opened chart, viewed labs), include the current `trace_id` in the ATNA message via the CATE extension. The platform can then aggregate ATNA events with CATE events by `trace_id` to build a unified timeline.
