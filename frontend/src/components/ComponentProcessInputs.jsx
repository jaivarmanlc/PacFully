import React from 'react';
import { MODULE_PROCESS_COLUMNS } from './ComponentProcessMatrix.jsx';

const FIELDS_BY_MODULE = {
  Kappa: [
    ['kappa_gsm_at_1mm', 'GSM', 'number'], ['kappa_thickness_mm', 'Thickness (mm)', 'number'],
    ['kappa_sheet_length_mm', 'Sheet L (mm)', 'number'], ['kappa_sheet_width_mm', 'Sheet W (mm)', 'number'],
    ['kappa_ups', 'UPS', 'number'], ['kappa_wastage_percent', 'Wastage (%)', 'number'],
    ['kappa_override_rate', 'Rate override (₹/kg)', 'number'],
  ],
  Insert: [
    ['kappa_gsm_at_1mm', 'GSM', 'number'], ['kappa_thickness_mm', 'Thickness (mm)', 'number'],
    ['kappa_sheet_length_mm', 'Sheet L (mm)', 'number'], ['kappa_sheet_width_mm', 'Sheet W (mm)', 'number'],
    ['kappa_ups', 'UPS', 'number'], ['kappa_wastage_percent', 'Wastage (%)', 'number'],
    ['kappa_override_rate', 'Rate override (₹/kg)', 'number'],
  ],
  Wrapper: [
    ['wrapper_gsm', 'GSM', 'number'], ['wrapper_ups', 'UPS', 'number'],
    ['wrapper_sheet_length_mm', 'Sheet L (mm)', 'number'], ['wrapper_sheet_width_mm', 'Sheet W (mm)', 'number'],
    ['wrapper_wastage_percent', 'Wastage (%)', 'number'], ['wrapper_make_ready_sheets', 'Make-ready', 'number'],
    ['wrapper_override_rate', 'Rate override (₹/kg)', 'number'],
  ],
  Printing: [
    ['print_method', 'Method', 'select', ['Offset', 'Digital']],
    ['print_colour_configuration', 'Colour configuration', 'select', ['1 Colour', '2 Colour', '4-Color CMYK', '5 Colour']],
    ['print_sheet_size', 'Sheet size', 'select', ['15x20', '20x28', '28x40']],
    ['print_override_rate', 'First-tier override (₹)', 'number'],
  ],
  Lamination: [
    ['lamination_type', 'Method', 'select', ['thermal', 'cold', 'dry']],
    ['lamination_finish', 'Finish', 'select', ['Matte', 'Gloss', 'Soft Touch', 'Other']],
    ['lamination_sheet_length_in', 'Sheet L (in)', 'number'], ['lamination_sheet_width_in', 'Sheet W (in)', 'number'],
    ['lam_override_rate', 'Rate override', 'number'],
  ],
  Punching: [
    ['punching_machine_rate_per_hour', 'Machine rate (₹/hr)', 'number'],
    ['punching_speed', 'Speed (sheets/hr)', 'number'], ['punching_setup_hours', 'Setup (hours)', 'number'],
  ],
  Glue: [
    ['glue_area_sq_in', 'Area (sq.in)', 'number'], ['glue_gsm', 'GSM', 'number'],
    ['glue_rate_per_kg', 'Rate (₹/kg)', 'number'],
  ],
  Embellishments: [
    ['embellishment_area_sq_in', 'Component area (sq.in)', 'number'],
    ['lamination_sheet_length_in', 'Sheet L (in)', 'number'], ['lamination_sheet_width_in', 'Sheet W (in)', 'number'],
    ['foiling_rate_per_100_sq_in', 'Foiling rate / 100 sq.in', 'number'],
    ['spot_uv_rate_per_100_sq_in', 'Spot UV rate / 100 sq.in', 'number'],
    ['drip_off_rate_per_100_sq_in', 'Drip-Off rate / 100 sq.in', 'number'],
    ['embossing_cost_per_box', 'Embossing (₹/box)', 'number'], ['debossing_cost_per_box', 'Debossing (₹/box)', 'number'],
  ],
  Accessories: [
    ['accessory_quantity_per_box', 'Qty / box', 'number'], ['accessory_unit_cost', 'Unit cost (₹)', 'number'],
  ],
  Conversion: [
    ['conversion_type', 'Method', 'select', ['Semi Automatic', 'Automatic', 'Contract']],
    ['conversion_semi_boxes_per_hour', 'Semi output (boxes/hr)', 'number'],
    ['conversion_semi_workers', 'Labour count', 'number'], ['conversion_monthly_salary', 'Salary / worker', 'number'],
    ['conversion_automatic_boxes_per_hour', 'Automatic output (boxes/hr)', 'number'],
    ['conversion_automatic_machine_rate', 'Machine rate (₹/hr)', 'number'],
    ['conversion_automatic_setup_rate', 'Setup rate (₹/hr)', 'number'],
    ['conversion_automatic_setup_hours', 'Setup time (hours)', 'number'],
    ['conversion_contract_rate_per_box', 'Contract rate (₹/box)', 'number'],
  ],
};

function getProcessRows(components, module) {
  const processes = MODULE_PROCESS_COLUMNS[module] || [];
  return components.flatMap((component, componentIndex) => {
    const active = processes.filter(process => component.processes?.[process] === true);
    if (module === 'Punching' && active.length > 1) {
      const foamMaterial = ['EVA', 'EPE', 'PU'].includes(component.material?.trim().toUpperCase());
      const chosen = foamMaterial || active.includes('Die Cutting') ? 'Die Cutting' : 'Punching';
      return [{ component, componentIndex, process: chosen }];
    }
    if (module === 'Punching' && active.length === 1 && ['EVA', 'EPE', 'PU'].includes(component.material?.trim().toUpperCase())) {
      return [{ component, componentIndex, process: 'Die Cutting' }];
    }
    return active.map(process => ({ component, componentIndex, process }));
  });
}

export default function ComponentProcessInputs({ module, components = [], onChange }) {
  const fields = FIELDS_BY_MODULE[module] || [];
  const rows = getProcessRows(components, module);
  if (!fields.length || !rows.length) return null;

  const updateInput = (row, key, value, type) => {
    const next = components.map((component, index) => {
      if (index !== row.componentIndex) return component;
      const processInputs = { ...(component.process_inputs || {}) };
      const values = { ...(processInputs[row.process] || {}) };
      if (value === '') delete values[key];
      else values[key] = type === 'number' ? Number(value) : value;
      if (Object.keys(values).length) processInputs[row.process] = values;
      else delete processInputs[row.process];
      return { ...component, process_inputs: processInputs };
    });
    onChange?.(next);
  };

  return (
    <section className="panel" style={{ padding: 0, overflow: 'hidden', marginBottom: 14 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
        <h3 className="panel-title" style={{ marginBottom: 3 }}>Component Process Inputs</h3>
        <p className="panel-sub">Blank fields inherit the shared module values. Enter a value here to override it for this component.</p>
      </div>
      <div className="table-wrap" style={{ overflowX: 'auto' }}>
        <table style={{ minWidth: 760 }}>
          <thead><tr><th style={{ position: 'sticky', left: 0, background: 'var(--panel)', zIndex: 1 }}>Component + Material</th><th>Process</th>{fields.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
          <tbody>{rows.map((row, rowIndex) => {
            const values = row.component.process_inputs?.[row.process] || row.component.process_inputs?.[module] || {};
            return (
              <tr key={`${row.component.component_name}|${row.component.material}|${row.process}|${rowIndex}`}>
                <td style={{ position: 'sticky', left: 0, background: 'var(--panel)', zIndex: 1, whiteSpace: 'nowrap' }}><strong>{row.component.component_name}_{row.component.material}</strong></td>
                <td>{row.process}</td>
                {fields.map(([key, label, type, options]) => (
                  <td key={key} style={{ minWidth: 150 }}>
                    {type === 'select' ? (
                      <select className="form-select" aria-label={`${label} for ${row.component.component_name}`} value={values[key] ?? ''} onChange={event => updateInput(row, key, event.target.value, type)}>
                        <option value="">Inherit</option>
                        {options.map(option => <option key={option} value={option}>{option}</option>)}
                      </select>
                    ) : (
                      <input className="form-input" type="number" step="any" aria-label={`${label} for ${row.component.component_name}`} placeholder="Inherit" value={values[key] ?? ''} onChange={event => updateInput(row, key, event.target.value, type)} />
                    )}
                  </td>
                ))}
              </tr>
            );
          })}</tbody>
        </table>
      </div>
    </section>
  );
}