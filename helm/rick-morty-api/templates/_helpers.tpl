{{- define "rick-morty-api.name" -}}
rick-morty-api
{{- end -}}

{{- define "rick-morty-api.fullname" -}}
{{- printf "%s" (include "rick-morty-api.name" .) -}}
{{- end -}}
