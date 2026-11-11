import {describe,it,expect} from 'vitest';
import {sum,money,eventCursor,dateLabel,statusLabel} from './lib';
describe('view rules',()=>{
 it('sums numbers without concatenating',()=>expect(sum([{n:2},{n:3}],'n')).toBe(5));
 it('does not invent values for missing data',()=>expect(sum([],'n')).toBe(0));
 it('formats cents as currency',()=>expect(money(2590,'en')).toContain('25.90'));
 it('never moves the event cursor backward',()=>expect(eventCursor(12,[{seq:7},{seq:12}])).toBe(12));
 it('takes the highest sequence',()=>expect(eventCursor(1,[{seq:3},{seq:2}])).toBe(3));
 it('translates state without changing identifier',()=>expect(statusLabel('reservado','en')).toBe('Reserved'));
 it('formats dates consistently in UTC',()=>expect(dateLabel('2025-01-01','en')).toContain('Jan'));
});
