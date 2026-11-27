import 'package:flutter/material.dart';

import '../../../core/api/models/hospital_models.dart';
import '../../../core/api/repositories/hospital_repository.dart';
import '../../../core/api/repositories/location_repository.dart';
import '../../../core/location/location_models.dart';
import '../../../core/location/location_service.dart';
import '../../../core/location/simulated_location_provider.dart';

class LocationHospitalsScreen extends StatefulWidget {
  const LocationHospitalsScreen({
    super.key,
    required this.hospitalRepository,
    this.locationRepository,
    this.subjectUserId,
  });

  final HospitalRepository hospitalRepository;
  final LocationRepository? locationRepository;
  final String? subjectUserId;

  @override
  State<LocationHospitalsScreen> createState() =>
      _LocationHospitalsScreenState();
}

class _LocationHospitalsScreenState extends State<LocationHospitalsScreen> {
  late final LocationService _locationService;
  bool _isLoading = false;
  String? _errorMessage;
  LocationReading? _currentLocation;
  List<NearbyHospital> _hospitals = [];
  String? _hospitalDisclaimer;
  String? _hospitalProvider;
  String? _updateStatus;

  @override
  void initState() {
    super.initState();
    _locationService = LocationService(provider: SimulatedLocationProvider());
    _resolveLocationAndFetchHospitals();
  }

  Future<void> _resolveLocationAndFetchHospitals() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _updateStatus = null;
    });

    try {
      final resolution = await _locationService.resolve(
        requestPermission: true,
      );

      if (resolution.isSuccess && resolution.reading != null) {
        final reading = resolution.reading!;
        setState(() {
          _currentLocation = reading;
        });

        // Submit to backend if repository is available
        if (widget.locationRepository != null && widget.subjectUserId != null) {
          try {
            await widget.locationRepository!.submitUpdate(
              subjectUserId: widget.subjectUserId!,
              latitude: reading.latitude,
              longitude: reading.longitude,
              accuracyMeters: reading.accuracyMeters,
              sourceKind: 'SIMULATED',
            );
            setState(() {
              _updateStatus = 'Location snapshot synchronized with backend.';
            });
          } catch (_) {
            setState(() {
              _updateStatus = 'Backend update unavailable (offline demo mode).';
            });
          }
        }

        // Fetch nearby hospitals
        final response = await widget.hospitalRepository.getNearbyHospitals(
          latitude: reading.latitude,
          longitude: reading.longitude,
          limit: 5,
        );

        setState(() {
          _hospitals = response.hospitals;
          _hospitalDisclaimer = response.disclaimer;
          _hospitalProvider = response.provider;
        });
      } else {
        setState(() {
          _errorMessage =
              resolution.failure?.message ?? 'Location resolution failed.';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load location or hospitals: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Location & Nearby Hospitals'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh location and hospitals',
            onPressed: _isLoading ? null : _resolveLocationAndFetchHospitals,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_errorMessage != null) ...[
                  Card(
                    color: theme.colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        _errorMessage!,
                        style: TextStyle(
                          color: theme.colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Location Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.my_location, color: Colors.blue),
                            const SizedBox(width: 8),
                            Text(
                              'Device Location',
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color:
                                    theme.colorScheme.surfaceContainerHighest,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                'SIMULATED',
                                style: theme.textTheme.labelSmall?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        if (_currentLocation != null) ...[
                          Text(
                            'Latitude: ${_currentLocation!.latitude.toStringAsFixed(5)}, Longitude: ${_currentLocation!.longitude.toStringAsFixed(5)}',
                            style: theme.textTheme.bodyMedium,
                          ),
                          if (_currentLocation!.accuracyMeters != null)
                            Text(
                              'Accuracy: ±${_currentLocation!.accuracyMeters!.toStringAsFixed(1)} m',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.outline,
                              ),
                            ),
                        ] else ...[
                          const Text('Location reading unavailable.'),
                        ],
                        if (_updateStatus != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            _updateStatus!,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.primary,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Disclaimer Banner
                Card(
                  color: theme.colorScheme.tertiaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.info_outline,
                              color: theme.colorScheme.onTertiaryContainer,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Hospital Directory Disclaimer',
                              style: theme.textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.onTertiaryContainer,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _hospitalDisclaimer ?? 'Seeded demonstration hospital data only. No hospital has been contacted, is confirmed available, or has accepted an incident.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onTertiaryContainer,
                          ),
                        ),
                        if (_hospitalProvider != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Provider: $_hospitalProvider',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: theme.colorScheme.onTertiaryContainer,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                Text(
                  'Nearby Emergency Facilities',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                if (_hospitals.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        'No hospital records returned for this location.',
                      ),
                    ),
                  )
                else
                  for (final hospital in _hospitals)
                    Card(
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      child: ListTile(
                        leading: const CircleAvatar(
                          child: Icon(Icons.local_hospital),
                        ),
                        title: Text(
                          hospital.name,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(hospital.address),
                            const SizedBox(height: 2),
                            Text(
                              'Distance: ${(hospital.distanceMeters / 1000).toStringAsFixed(2)} km · [${hospital.sourceKind}]',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.outline,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ),
    );
  }
}
