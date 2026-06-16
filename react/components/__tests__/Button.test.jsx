import '@testing-library/jest-dom/vitest';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import Button from '../Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('defaults to outlined variant', () => {
    render(<Button>Outlined</Button>);
    const button = screen.getByText('Outlined').closest('button');
    expect(button).toHaveClass('MuiButton-outlined');
  });

  it('accepts contained variant', () => {
    render(<Button variant="contained">Contained</Button>);
    const button = screen.getByText('Contained').closest('button');
    expect(button).toHaveClass('MuiButton-contained');
  });
});
