export const STATUSES = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'];
export const ACTIVE_STATUSES = ['PENDING', 'PROCESSING'];

export const STATUS_LABELS = {
  PENDING: 'Pending',
  PROCESSING: 'Processing',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
  CANCELLED: 'Cancelled',
};

export const PRIORITIES = [
  { value: 'LOW', label: 'Low' },
  { value: 'NORMAL', label: 'Normal' },
  { value: 'HIGH', label: 'High' },
  { value: 'URGENT', label: 'Urgent' },
];

export const CATEGORIES = [
  { value: 'REPAIR', label: 'Repair' },
  { value: 'INSTALLATION', label: 'Installation' },
  { value: 'MAINTENANCE', label: 'Maintenance' },
  { value: 'INSPECTION', label: 'Inspection' },
  { value: 'SUPPORT', label: 'Support' },
];

export const labelOf = (list, value) => list.find((x) => x.value === value)?.label ?? value;
