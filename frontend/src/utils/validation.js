import { CATEGORIES, PRIORITIES } from '../constants';

/**
 * Client-side validation. It mirrors the backend serializer rules so users get
 * instant feedback, but the server remains the source of truth.
 */
export function validateRequestForm(values) {
  const errors = {};
  const title = values.title.trim();
  const description = values.description.trim();

  if (title.length < 5) errors.title = 'Title must be at least 5 characters.';
  else if (title.length > 200) errors.title = 'Title must be 200 characters or fewer.';

  if (description.length < 10) errors.description = 'Please describe the problem (at least 10 characters).';
  else if (description.length > 5000) errors.description = 'Description must be 5000 characters or fewer.';

  if (!CATEGORIES.some((c) => c.value === values.category)) errors.category = 'Choose a category.';
  if (!PRIORITIES.some((p) => p.value === values.priority)) errors.priority = 'Choose a priority.';
  return errors;
}

export function validateRegisterForm(values) {
  const errors = {};
  if (values.username.trim().length < 3) errors.username = 'Username must be at least 3 characters.';
  if (values.email && !/^\S+@\S+\.\S+$/.test(values.email)) errors.email = 'Enter a valid email address.';
  if (values.password.length < 8) errors.password = 'Password must be at least 8 characters.';
  return errors;
}
