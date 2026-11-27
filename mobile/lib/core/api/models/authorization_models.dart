import 'json_helpers.dart';

class AuthorizedSubject {
  const AuthorizedSubject({
    required this.subjectUserId,
    required this.grantedAt,
    this.revokedAt,
  });

  final String subjectUserId;
  final DateTime grantedAt;
  final DateTime? revokedAt;

  factory AuthorizedSubject.fromJson(Map<String, dynamic> json) {
    return AuthorizedSubject(
      subjectUserId: requiredString(json, 'subject_user_id'),
      grantedAt: requiredDateTime(json, 'granted_at'),
      revokedAt: optionalDateTime(json, 'revoked_at'),
    );
  }

  Map<String, dynamic> toJson() => {
    'subject_user_id': subjectUserId,
    'granted_at': grantedAt.toIso8601String(),
    if (revokedAt != null) 'revoked_at': revokedAt?.toIso8601String(),
  };
}

class AuthorizedSubjectsResponse {
  const AuthorizedSubjectsResponse({required this.authorizedSubjects});

  final List<AuthorizedSubject> authorizedSubjects;

  factory AuthorizedSubjectsResponse.fromJson(Map<String, dynamic> json) {
    final raw = json['authorized_subjects'];
    final list = (raw is List)
        ? raw
              .map(
                (item) =>
                    AuthorizedSubject.fromJson(item as Map<String, dynamic>),
              )
              .toList(growable: false)
        : const <AuthorizedSubject>[];
    return AuthorizedSubjectsResponse(authorizedSubjects: list);
  }

  Map<String, dynamic> toJson() => {
    'authorized_subjects': authorizedSubjects.map((s) => s.toJson()).toList(),
  };
}
