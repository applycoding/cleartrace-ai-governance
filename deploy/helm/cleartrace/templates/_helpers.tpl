{{- define "cleartrace.name" -}}
cleartrace
{{- end }}

{{- define "cleartrace.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "cleartrace.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "cleartrace.labels" -}}
app.kubernetes.io/name: {{ include "cleartrace.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "cleartrace.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cleartrace.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
