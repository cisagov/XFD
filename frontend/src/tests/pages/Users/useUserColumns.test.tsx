import { it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useUserColumns } from '@/pages/Users/useUserColumns';

const noop = vi.fn();

const baseProps = {
  setSelectedRow: noop,
  setFormValues: noop,
  setEditUserDialogOpen: noop,
  setDeleteUserDialogOpen: noop
};

it('returns user columns', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: null,
      ...baseProps
    })
  );

  const fields = result.current.map((col) => col.field);

  expect(fields).toContain('full_name');
  expect(fields).toContain('email');
  expect(fields).toContain('edit');
});

it('limits string columns to equals and contains filters', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: null,
      ...baseProps
    })
  );

  const nameCol = result.current.find((col) => col.field === 'full_name');

  expect(nameCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('restricts Approval Date filter operators', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: null,
      ...baseProps
    })
  );

  const approvalDateCol = result.current.find(
    (col) => col.field === 'date_approved'
  );

  expect(approvalDateCol?.type).toBe('string');
  expect(approvalDateCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('restricts Last Logged In filter operators', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: null,
      ...baseProps
    })
  );

  const lastLoginCol = result.current.find(
    (col) => col.field === 'lastLoggedInString'
  );

  expect(lastLoginCol?.type).toBe('string');
  expect(lastLoginCol?.filterOperators?.map((op) => op.value)).toEqual(
    expect.arrayContaining(['equals', 'contains'])
  );
});

it('adds delete column for global admin users', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: { user_type: 'globalAdmin' },
      ...baseProps
    })
  );

  const deleteCol = result.current.find((col) => col.field === 'delete');

  expect(deleteCol).toBeDefined();
  expect(deleteCol?.filterable).toBe(false);
});

it('does not add delete column for non-admin users', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: { user_type: 'regionalAdmin' },
      ...baseProps
    })
  );

  const deleteCol = result.current.find((col) => col.field === 'delete');

  expect(deleteCol).toBeUndefined();
});

it('keeps action columns non-filterable', () => {
  const { result } = renderHook(() =>
    useUserColumns({
      user: null,
      ...baseProps
    })
  );

  const editCol = result.current.find((col) => col.field === 'edit');

  expect(editCol?.filterable).toBe(false);
  expect(editCol?.filterOperators).toBeUndefined();
});
