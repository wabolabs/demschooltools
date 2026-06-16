import '@testing-library/jest-dom/vitest';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import PageTitle from '../PageTitle';

describe('PageTitle', () => {
  it('renders children', () => {
    render(<PageTitle>Test Title</PageTitle>);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('renders as an h3', () => {
    render(<PageTitle>Title</PageTitle>);
    const heading = screen.getByText('Title');
    expect(heading.tagName).toBe('H3');
  });
});
