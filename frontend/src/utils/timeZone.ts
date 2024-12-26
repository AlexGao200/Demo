/**
 * Get the user's time zone.
 * @returns {string} The user's time zone in IANA format (e.g., "America/New_York").
 */
export function getUserTimeZone(): string {
  try {
    // Get the time zone using Intl.DateTimeFormat
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return timeZone;
  } catch (error) {
    console.error('Error getting user time zone:', error);
    // Return a default time zone if unable to determine
    return 'UTC';
  }
}
