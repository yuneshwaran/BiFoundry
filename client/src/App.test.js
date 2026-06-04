import { render, screen } from '@testing-library/react';
import App from './App';

test('renders project hub page', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /project hub/i })).toBeInTheDocument();
});
