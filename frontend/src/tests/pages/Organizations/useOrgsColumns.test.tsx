import { it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useOrgsColumns } from '@/pages/Organizations/useOrgsColumns';

const noop = vi.fn();

const baseProps = {
  setSelectedRow: noop,
  setFormValues: noop,
  setEditUserDialogOpen: noop,
  setDeleteUserDialogOpen: noop
};

it('returns user columns', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const fields = result.current.map((col) => col.field);

  expect(fields).toContain('name');
  expect(fields).toContain('acronym');
  expect(fields).toContain('state');
  expect(fields).toContain('region_id');
  expect(fields).toContain('view');
});

it('restricts name filter operators', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const nameCol = result.current.find((col) => col.field === 'name');

  expect(nameCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('restricts acronym filter operators', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const acronymCol = result.current.find((col) => col.field === 'acronym');

  expect(acronymCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('restricts state filter operators', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const stateCol = result.current.find((col) => col.field === 'state');

  expect(stateCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('restricts region_id filter operators', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const regionCol = result.current.find((col) => col.field === 'region_id');

  expect(regionCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('keeps action columns non-filterable', () => {
  const { result } = renderHook(() => useOrgsColumns());

  const editCol = result.current.find((col) => col.field === 'view');

  expect(editCol?.filterable).toBe(false);
  expect(editCol?.filterOperators).toBeUndefined();
});
