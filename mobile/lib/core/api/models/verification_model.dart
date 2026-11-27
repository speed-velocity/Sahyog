class VerificationRequest {
  const VerificationRequest({
    required this.idempotencyKey,
    this.requestReference,
  });

  final String idempotencyKey;
  final String? requestReference;

  Map<String, dynamic> toJson() => {
    'response': 'I_AM_OK',
    'idempotency_key': idempotencyKey,
    if (requestReference != null) 'request_reference': requestReference,
  };
}
