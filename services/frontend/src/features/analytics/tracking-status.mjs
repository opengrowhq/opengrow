export function trackingStatusLabel(status) {
  return status?.installed ? "Installed" : "Not installed";
}

export function trackingStatusDetail(status) {
  if (!status?.installed) {
    return "No events yet";
  }
  const events = Number(status.events ?? 0);
  const visits = Number(status.first_party_visits ?? 0);
  const conversions = Number(status.first_party_conversions ?? 0);
  return `${events} events · ${visits} visits · ${conversions} conversions`;
}

export function trackingStatusTone(status) {
  return status?.installed ? "installed" : "pending";
}
