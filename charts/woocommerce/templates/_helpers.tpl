{{- define "woocommerce.fullname" -}}
{{- if .Values.wordpress.fullnameOverride }}
{{- .Values.wordpress.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
