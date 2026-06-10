import React from 'react';
import { render } from '@testing-library/react';
import CanvasGrid from './CanvasGrid';

const mockGridProps = {};

jest.mock('react-grid-layout', () => {
  const React = require('react');
  const GridLayout = (props) => {
    Object.assign(mockGridProps, props);
    return <div data-testid="grid-layout">{props.children}</div>;
  };

  return {
    __esModule: true,
    default: GridLayout,
    WidthProvider: (Component) => Component,
  };
});

describe('CanvasGrid', () => {
  beforeEach(() => {
    Object.keys(mockGridProps).forEach((key) => delete mockGridProps[key]);
  });

  it('does not persist layout changes while controlled props are reconciling', () => {
    const onLayoutChange = jest.fn();
    const { rerender } = render(
      <CanvasGrid
        activePage={{ id: 1, width: 1280, visuals: [{ id: 10, x: 0, y: 0, w: 3, h: 2, template_key: 'card' }] }}
        templates={[]}
        onLayoutChange={onLayoutChange}
        onDropTemplate={jest.fn()}
        onSelectVisual={jest.fn()}
        onDeleteVisual={jest.fn()}
        selectedVisualId={10}
      />,
    );

    rerender(
      <CanvasGrid
        activePage={{ id: 1, width: 1280, visuals: [{ id: 10, x: 4, y: 2, w: 5, h: 3, template_key: 'card' }] }}
        templates={[]}
        onLayoutChange={onLayoutChange}
        onDropTemplate={jest.fn()}
        onSelectVisual={jest.fn()}
        onDeleteVisual={jest.fn()}
        selectedVisualId={10}
      />,
    );

    expect(mockGridProps.onLayoutChange).toBeUndefined();
    expect(mockGridProps.layout).toEqual([{ i: '10', x: 4, y: 2, w: 5, h: 3 }]);
    expect(onLayoutChange).not.toHaveBeenCalled();
  });

  it('persists layout after drag and resize interactions finish', () => {
    const onLayoutChange = jest.fn();
    render(
      <CanvasGrid
        activePage={{ id: 1, width: 1280, visuals: [{ id: 10, x: 0, y: 0, w: 3, h: 2, template_key: 'card' }] }}
        templates={[]}
        onLayoutChange={onLayoutChange}
        onDropTemplate={jest.fn()}
        onSelectVisual={jest.fn()}
        onDeleteVisual={jest.fn()}
        selectedVisualId={10}
      />,
    );

    const nextLayout = [{ i: '10', x: 1, y: 2, w: 4, h: 3 }];
    mockGridProps.onDragStop(nextLayout);
    mockGridProps.onResizeStop(nextLayout);

    expect(onLayoutChange).toHaveBeenNthCalledWith(1, nextLayout);
    expect(onLayoutChange).toHaveBeenNthCalledWith(2, nextLayout);
  });
});
