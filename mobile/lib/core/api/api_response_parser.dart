import 'api_exception.dart';

Map<String, dynamic> requireJsonObject(Object? value, String context) {
  if (value is Map<String, dynamic>) return value;
  throw ApiException(
    type: ApiExceptionType.invalidResponse,
    message: 'The backend returned an unreadable $context response.',
    details: value,
  );
}

T parseApiObject<T>(
  Object? value,
  String context,
  T Function(Map<String, dynamic>) parse,
) {
  final object = requireJsonObject(value, context);
  try {
    return parse(object);
  } on FormatException catch (error) {
    throw ApiException(
      type: ApiExceptionType.invalidResponse,
      message: 'The backend $context response is missing valid fields.',
      details: error.message,
    );
  }
}
