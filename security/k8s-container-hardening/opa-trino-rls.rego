# Trino row-level security via OPA (G-004 identity propagation).
# Input expects end-user identity from Kerberos (PowerBI) or oauthPassThru (Grafana).
# Fail closed: missing/malformed identity => deny.

package trino.authz

import future.keywords.if
import future.keywords.in

default allow := false

# Classification ordinal — higher may not read down into higher labels.
class_rank["U"] := 0
class_rank["FOUO"] := 1
class_rank["SECRET"] := 2
class_rank["TS"] := 3

identity_present if {
  input.user.name
  input.user.name != ""
  input.user.classification
  count(input.user.mission_ids) > 0
}

allow if {
  identity_present
  input.action == "SelectFromColumns"
  input.table.catalog == "mission_marts"
  input.table.schema == "reporting"
  row_permitted
}

row_permitted if {
  some mission_id in input.user.mission_ids
  mission_id == input.resource.mission_id
  class_rank[input.user.classification] >= class_rank[input.resource.classification]
}

deny_reason := "missing_or_unmapped_end_user_identity" if {
  not identity_present
}

deny_reason := "row_not_permitted_for_principal" if {
  identity_present
  not row_permitted
}
