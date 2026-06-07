/**
 * @package   EGI-STAT/frontend/lib
 * @author    Padmin D. Curtis (AI) for Fabio Cherici
 * @version   1.0.0 (EGI-STAT)
 * @date      2026-06-07
 * @purpose   Test formatChartLabel — la label del grafico deve mostrare i decimali
 *            per valori frazionari (CL/PI/weighted), restando intera per i conteggi.
 *            Cattura il bug M-242: Math.round collassava 2.4 -> "2".
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatChartLabel } from './formatChartLabel.js';

test('valore frazionario mostra almeno un decimale', () => {
  assert.equal(formatChartLabel(2.4), '2.4');
  assert.equal(formatChartLabel(2.33), '2.33');
});

test('valore frazionario arrotonda a max 2 decimali', () => {
  assert.equal(formatChartLabel(2.456), '2.46');
});

test('valore intero resta intero (conteggi: missions/files)', () => {
  assert.equal(formatChartLabel(3), '3');
  assert.equal(formatChartLabel(0), '0');
});

test('non-numero passa invariato', () => {
  assert.equal(formatChartLabel('N/A'), 'N/A');
});
