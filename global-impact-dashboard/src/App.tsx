/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Route, Routes } from 'react-router-dom';

import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Scenario from './pages/Scenario';

/**
 * Router shell. Pages own their own layout (Navbar, ambient bg, etc.)
 * so we keep this file tiny and add new routes here.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/scenario" element={<Scenario />} />
      {/* Fallback: anything unknown lands on the dashboard. */}
      <Route path="*" element={<Dashboard />} />
    </Routes>
  );
}
