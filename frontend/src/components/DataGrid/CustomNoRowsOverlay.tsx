import * as React from 'react';
import { GridOverlay } from '@mui/x-data-grid';

export default function CustomNoRowsOverlay(props: any) {
  return (
    <GridOverlay
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {props.children}
    </GridOverlay>
  );
}
