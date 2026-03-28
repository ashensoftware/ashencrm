import { expect, test, describe } from 'vitest';
import { mapStatusToColor, mapStatusToLabel } from '../utils/statusMapper';

describe('Status Mapper', () => {
  test('returns correct label for valid status', () => {
    expect(mapStatusToLabel('scraped')).toBe('Potencial');
    expect(mapStatusToLabel('demo_created')).toBe('Demo Lista');
  });

  test('returns fallback format for unknown status', () => {
    expect(mapStatusToLabel('unknown_status')).toBe('unknown_status');
    expect(mapStatusToLabel()).toBe('—');
  });

  test('returns specific color for scraped', () => {
    expect(mapStatusToColor('scraped')).toBe('#8b5cf6');
  });
});
