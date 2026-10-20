import React from 'react';
import { X, Calculator } from 'lucide-react';
import { CalcTracePanel, money } from './CostCard.jsx';
import { MODULE_PROCESS_COLUMNS } from './ComponentProcessMatrix.jsx';

const mmToInches = value => Number(value) / 25.4;

const FIELDS_BY_MODULE = {
  Kappa: [
    ['kappa_gsm_at_1mm', 'GSM', 'number'], ['kappa_thickness_mm', 'Thickness (mm)', 'number'],
    ['kappa_sheet_length_mm', 'Sheet L (in)', 'inches'], ['kappa_sheet_width_mm', 'Sheet W (in)', 'inches'],
    ['kappa_ups', 'UPS', 'number'], ['kappa_wastage_percent', 'Wastage (%)', 'number'],
    ['kappa_override_rate', 'Component override (₹/kg)', 'number'],
  ],
  Insert: [
    ['insert_gsm', 'GSM', 'number'], ['insert_ups', 'UPS', 'number'],
    ['insert_sheet_length_mm', 'Sheet L (in)', 'inches'], ['insert_sheet_width_mm', 'Sheet W (in)', 'inches'],
    ['insert_pricing_method', 'Foam insert pricing', 'select', ['Thickness-based', 'Fixed per insert', 'Per kg']],
    ['insert_thickness_mm', 'Insert thickness (mm)', 'number'], ['insert_quantity_per_box', 'Pieces / box', 'number'],
    ['insert_weight_g_per_piece', 'Weight / insert (g)', 'number'],
    ['kappa_wastage_percent', 'Wastage (%)', 'number'],
    ['kappa_override_rate', 'Rate override (₹/kg)', 'number'],
  ],
  Wrapper: [
    ['wrapper_gsm', 'GSM', 'number'], ['wrapper_ups', 'UPS', 'number'],
    ['wrapper_sheet_length_mm', 'Sheet L (in)', 'inches'], ['wrapper_sheet_width_mm', 'Sheet W (in)', 'inches'],
    ['wrapper_wastage_percent', 'Wastage (%)', 'number'], ['wrapper_make_ready_sheets', 'Make-ready', 'number'],
    ['wrapper_override_rate', 'Rate override (₹/kg)', 'number'],
  ],
  Printing: [
    ['print_method', 'Method', 'select', ['Offset', 'Digital']],
    ['print_colour_configuration', 'Colour configuration', 'text', ['1 Colour', '2 Colour', '4-Color CMYK', '5 Colour']],
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
    ['drip_off_rate_per_100_sq_in', 'Drip-Off rate / 100 sq.in', 'select', [
      { value: '0.9', label: '₹0.90' },
      { value: '0.95', label: '₹0.95' },
    ]],
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
  'One Time Cost': [
    ['tooling_type', 'Tooling type', 'select', ['Punching Die', 'Emboss/Deboss Die', 'Foil Stamp Die']],
    ['sheet_size', 'Die sheet size', 'select', ['15x20', '20x28', '25x36', '28x40']],
    ['area_sq_cm', 'Die area (sq.cm)', 'number'],
  ],
};

function inheritedMasterValue(module, key, component, values, masterRates, estimateDefaults, sharedOverrideRate) {
  const estimateOverrideKey = {
    Kappa: 'kappa_override_rate',
    Insert: 'kappa_override_rate',
    Wrapper: 'wrapper_override_rate',
    Printing: 'print_override_rate',
    Lamination: 'lam_override_rate',
  }[module];
  const estimateOverride = key === estimateOverrideKey
    ? (module === 'Kappa' || module === 'Insert' ? sharedOverrideRate : estimateDefaults[key])
    : null;
  if (estimateOverride != null && estimateOverride !== '') {
    const unit = ['kappa_override_rate', 'wrapper_override_rate'].includes(key) ? '/kg' : '';
    return `Estimate ₹${Number(estimateOverride).toFixed(2)}${unit}`;
  }
  const material = component.material?.trim().toUpperCase() || '';
  const rateForMaterial = material.includes('FBB') ? 'fbb_rate_per_kg'
    : material.includes('DUPLEX') ? 'duplex_board_rate_per_kg' : 'kappa_rate_per_kg';
  const sheetSize = String(values.print_sheet_size || '28x40').toLowerCase().replace('×', 'x').replace(/\s/g, '');
  const laminationType = String(values.lamination_type || 'thermal').trim().toLowerCase();
  const laminationFinish = String(values.lamination_finish || 'Matte').trim().toLowerCase().replace(/\s/g, '_');
  const laminationFinishRate = masterRates[`lamination_rate_${laminationType}_${laminationFinish}`];
  const masterKeys = {
    Kappa: {
      kappa_wastage_percent: 'kappa_wastage_percent',
      kappa_override_rate: rateForMaterial,
    },
    Insert: {
      kappa_wastage_percent: 'kappa_wastage_percent',
      kappa_override_rate: rateForMaterial,
      foam_insert_rate_per_10mm: 'foam_insert_rate_per_10mm',
      foam_insert_fixed_rate_per_piece: 'foam_insert_fixed_rate_per_piece',
      foam_insert_rate_per_kg: 'foam_insert_rate_per_kg',
    },
    Wrapper: {
      wrapper_wastage_percent: 'wrapper_wastage_percent',
      wrapper_make_ready_sheets: 'wrapper_make_ready_sheets',
      wrapper_override_rate: 'wrapper_rate_per_kg',
    },
    Printing: {
      print_override_rate: `print_${sheetSize}_first`,
    },
    Lamination: {
      lam_override_rate: laminationFinishRate > 0
        ? `lamination_rate_${laminationType}_${laminationFinish}`
        : `lamination_${laminationType}`,
    },
    Punching: {
      punching_machine_rate_per_hour: 'punching_machine_rate_per_hour',
      punching_speed: material.includes('ART PAPER') || material.includes('WRAPPER') ? 'punching_speed_wrapper'
        : material.includes('FBB') ? 'punching_speed_fbb'
          : material.includes('DUPLEX') ? 'punching_speed_duplex'
            : ['EVA', 'EPE', 'PU'].includes(material) ? 'punching_speed_foam' : 'punching_speed_kappa',
      punching_setup_hours: 'punching_setup_hours',
    },
    Glue: {
      glue_rate_per_kg: 'glue_rate_per_kg',
    },
    Embellishments: {
      embellishment_rate_per_sq_in: 'embellishment_rate_per_sq_in',
      embellishment_setup: 'embellishment_setup',
      embellishment_minimum: 'embellishment_minimum',
      foiling_rate_per_100_sq_in: 'foiling_rate_per_100_sq_in',
      spot_uv_rate_per_100_sq_in: 'spot_uv_rate_per_100_sq_in',
      embossing_cost_per_box: 'embossing_cost_per_box',
      debossing_cost_per_box: 'debossing_cost_per_box',
    },
    Conversion: {
      conversion_semi_boxes_per_hour: 'conversion_semi_boxes_per_hour',
      conversion_semi_workers: 'conversion_semi_workers',
      conversion_monthly_salary: 'conversion_monthly_salary',
      conversion_automatic_boxes_per_hour: 'conversion_automatic_boxes_per_hour',
      conversion_automatic_machine_rate: 'conversion_automatic_machine_rate',
      conversion_automatic_setup_rate: 'conversion_automatic_setup_rate',
      conversion_automatic_setup_hours: 'conversion_automatic_setup_hours',
      conversion_contract_rate_per_box: 'conversion_contract_rate_per_box',
    },
    'One Time Cost': {},
  };

  if (module === 'Conversion') {
    masterKeys.Conversion.conversion_working_days = 'conversion_working_days';
    masterKeys.Conversion.conversion_hours_per_day = 'conversion_hours_per_day';
  }
  if (module === 'One Time Cost' && values.tooling_type) {
    if (values.tooling_type === 'Punching Die' && values.sheet_size) {
      masterKeys['One Time Cost'].sheet_size = `punching_die_${values.sheet_size}`;
    } else if (values.tooling_type === 'Emboss/Deboss Die') {
      masterKeys['One Time Cost'].area_sq_cm = 'emboss_deboss_die_rate_per_sq_cm';
    } else if (values.tooling_type === 'Foil Stamp Die') {
      masterKeys['One Time Cost'].area_sq_cm = 'foil_stamp_die_rate_per_sq_cm';
    }
  }

  const masterKey = masterKeys[module]?.[key];
  const masterValue = masterKey ? masterRates[masterKey] : null;
  if (masterValue != null && masterValue !== '') {
    return `Master: ${Number(masterValue).toLocaleString(undefined, { maximumFractionDigits: 4 })}`;
  }

  const estimateValue = estimateDefaults[key];
  if (estimateValue != null && estimateValue !== '' && estimateValue !== 'inherit') {
    return `Estimate: ${estimateValue}`;
  }
  const applicationDefaults = {
    print_method: 'Offset (PDF components still require confirmation)',
    print_sheet_size: '28x40',
    lamination_type: 'thermal',
    lamination_finish: 'Matte',
    conversion_type: 'Semi Automatic',
  };
  if (applicationDefaults[key]) {
    return `Default: ${applicationDefaults[key]}`;
  }
  return '';
}

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

export default function ComponentProcessInputs({
  module,
  masterRates = {},
  estimateDefaults = {},
  sharedOverrideRate,
  components = [],
  onChange,
  onCalculateModuleComponents,
  calculationDetailsOpen,
  onCloseCalculationDetails,
  componentCalculation,
  calculatingComponent,
}) {
  const fields = FIELDS_BY_MODULE[module] || [];
  const rows = getProcessRows(components, module);
  if (!fields.length || (!rows.length && module !== 'Kappa')) return null;
  const moduleLabel = module === 'Kappa' ? 'Base Material' : module;

  const updateInput = (row, key, value, type) => {
    const next = components.map((component, index) => {
      if (index !== row.componentIndex) return component;
      const processInputs = { ...(component.process_inputs || {}) };
      const moduleValues = module === row.process ? null : { ...(processInputs[module] || {}) };
      const values = { ...(processInputs[row.process] || {}) };
      if (value === '') {
        delete values[key];
        if (moduleValues) delete moduleValues[key];
      }
      else values[key] = type === 'number' || type === 'inches' ? Number(value) : value;
      if (module === row.process) {
        if (Object.keys(values).length) processInputs[module] = values;
        else delete processInputs[module];
      } else {
        if (Object.keys(values).length) processInputs[row.process] = values;
        else delete processInputs[row.process];
        if (Object.keys(moduleValues).length) processInputs[module] = moduleValues;
        else delete processInputs[module];
      }
      return { ...component, process_inputs: processInputs };
    });
    onChange?.(next);
  };

  return (
    <section className="panel component-process-panel">
      <div className="component-process-heading">
        <div>
          <h3 className="panel-title" style={{ marginBottom: 3 }}>{moduleLabel} Components</h3>
          <p className="panel-sub">
            {module === 'Kappa'
              ? 'Review extracted values below. Open the calculation to view cost breakdowns for all Base Material components.'
              : 'Blank fields use the value shown below when a default is available. Open the calculation to view breakdowns for all components.'}
          </p>
        </div>
        {rows.length > 0 && (
          <button
            className="btn btn-secondary btn-sm"
            type="button"
            disabled={calculatingComponent}
            onClick={onCalculateModuleComponents}
          >
            <Calculator size={13} />
            {calculatingComponent && componentCalculation?.module === module
              ? 'Calculating...'
              : `${moduleLabel} Calculation`}
          </button>
        )}
      </div>
      <div className="component-process-list">
        {rows.map((row, rowIndex) => {
          const isFoamInsert = ['EVA', 'EPE', 'PU'].includes(row.component.material?.trim().toUpperCase());
          const componentValues = {
            ...(row.component.process_inputs?.[module] || {}),
            ...(row.component.process_inputs?.[row.process] || {}),
          };
          const values = { ...estimateDefaults, ...componentValues };
          if (module === 'Lamination') {
            const material = row.component.material?.trim().toUpperCase() || '';
            const sheetProcess = material.includes('ART PAPER') || material.includes('WRAPPER') ? 'Wrapper'
              : material.includes('DUPLEX') || material.includes('FBB') ? 'Insert'
                : material.includes('KAPPA') ? 'Kappa' : null;
            const sheetInputs = sheetProcess ? row.component.process_inputs?.[sheetProcess] || {} : {};
            if (componentValues.lamination_sheet_length_in == null && sheetInputs[`${sheetProcess?.toLowerCase()}_sheet_length_mm`] != null) {
              values.lamination_sheet_length_in = mmToInches(sheetInputs[`${sheetProcess.toLowerCase()}_sheet_length_mm`]);
            }
            if (componentValues.lamination_sheet_width_in == null && sheetInputs[`${sheetProcess?.toLowerCase()}_sheet_width_mm`] != null) {
              values.lamination_sheet_width_in = mmToInches(sheetInputs[`${sheetProcess.toLowerCase()}_sheet_width_mm`]);
            }
          }
          const visibleFields = module === 'One Time Cost'
            ? fields.filter(([key]) => key === 'tooling_type'
              || (values.tooling_type === 'Punching Die' && key === 'sheet_size')
              || (['Emboss/Deboss Die', 'Foil Stamp Die'].includes(values.tooling_type) && key === 'area_sq_cm'))
            : module === 'Insert'
            ? fields.filter(([key]) => isFoamInsert
              ? ['insert_pricing_method', 'insert_thickness_mm', 'insert_quantity_per_box', 'insert_weight_g_per_piece'].includes(key)
              : !['insert_pricing_method', 'insert_thickness_mm', 'insert_quantity_per_box', 'insert_weight_g_per_piece'].includes(key))
            : fields;
          const inputValues = Object.fromEntries(Object.entries(componentValues).map(([key, value]) => [
            key,
            typeof value === 'string' && (!value.trim() || value.trim().toLowerCase() === 'inherit') ? '' : value,
          ]));
          return (
            <article className={`component-process-row module-component-row${module === 'Kappa' ? ' kappa-component-row' : ''}`} style={{ '--component-field-count': visibleFields.length }} key={`${row.component.component_name}|${row.component.material}|${row.process}|${rowIndex}`}>
              <div className="component-process-row-heading">
                <strong>{row.component.component_name}_{row.component.material}</strong>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="pill pill-blue">{row.process}</span>
                </div>
              </div>
              <div className="component-process-fields">
                {visibleFields.map(([key, label, type, options]) => (
                  (() => {
                    const inheritedDescription = inheritedMasterValue(
                      module, key, row.component, values, masterRates, estimateDefaults, sharedOverrideRate,
                    );
                    const selectValue = inputValues[key] || values[key] || estimateDefaults[key] || '';
                    return (
                      <div className="form-group" key={key}>
                    <label className="form-label" htmlFor={`${module}-${rowIndex}-${key}`}>
                      {module === 'Kappa' && key === 'kappa_override_rate' ? 'Component override (₹/kg)' : label}
                    </label>
                    {type === 'select' ? (
                      <select id={`${module}-${rowIndex}-${key}`} className="form-select" value={selectValue} onChange={event => updateInput(row, key, event.target.value, type)}>
                        {!selectValue && <option value="">{inheritedDescription || 'Select value'}</option>}
                        {options.map(option => typeof option === 'string'
                          ? <option key={option} value={option}>{option}</option>
                          : <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    ) : (
                      <>
                        <input
                          id={`${module}-${rowIndex}-${key}`}
                          className="form-input"
                          type={type === 'text' ? 'text' : 'number'}
                          step={type === 'text' ? undefined : 'any'}
                          list={type === 'text' ? `${module}-${rowIndex}-${key}-suggestions` : undefined}
                          placeholder={inheritedDescription || 'Enter required value'}
                          title={inheritedDescription || 'No Master Configuration default; enter this component value.'}
                          value={type === 'inches'
                            ? Number.isFinite(Number(inputValues[key] ?? values[key])) && (inputValues[key] ?? values[key]) !== ''
                              ? Number(((inputValues[key] ?? values[key]) / 25.4).toFixed(2)) : ''
                            : inputValues[key] ?? values[key] ?? ''}
                          onChange={event => updateInput(row, key, event.target.value === '' ? '' : type === 'inches' ? Number(event.target.value) * 25.4 : event.target.value, type)}
                        />
                        {type === 'text' && options?.length > 0 && (
                          <datalist id={`${module}-${rowIndex}-${key}-suggestions`}>
                            {options.map(option => <option key={option} value={option} />)}
                          </datalist>
                        )}
                      </>
                    )}
                      </div>
                    );
                  })()
                ))}
              </div>
            </article>
          );
        })}
        {!rows.length && <p className="component-process-empty">No components are currently assigned to {module === 'Kappa' ? 'Base Material' : module}.</p>}
      </div>
      {calculationDetailsOpen && (
        <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onCloseCalculationDetails?.(); }}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="component-calculation-details-title" style={{ width: 900, maxWidth: 'calc(100vw - 32px)', maxHeight: '88vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <div>
                <span className="eyebrow">{moduleLabel}</span>
                <h2 id="component-calculation-details-title">Component Calculation Details</h2>
                <p className="panel-sub" style={{ margin: '4px 0 0' }}>{moduleLabel} component calculations</p>
              </div>
              <button className="modal-close" type="button" aria-label={`Close ${moduleLabel} calculation`} onClick={() => onCloseCalculationDetails?.()}><X size={16} /></button>
            </div>
            {calculatingComponent && componentCalculation?.module === module && (
              <div className="info-banner">Calculating {moduleLabel} components…</div>
            )}
            {componentCalculation?.module === module && componentCalculation.error && (
              <div className="warn-banner" role="alert" style={{ marginTop: 14 }}>{componentCalculation.error}</div>
            )}
            {componentCalculation?.module === module && componentCalculation.failures?.length > 0 && (
              <div className="warn-banner" role="alert" style={{ marginTop: 14 }}>
                <strong>Some {moduleLabel} components need configuration:</strong>
                <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>
                  {componentCalculation.failures.map((failure, index) => (
                    <li key={`${failure.component_label}-${index}`}>
                      {failure.component_label ? `${failure.component_label}: ` : ''}{failure.detail}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {componentCalculation?.module === module && componentCalculation.lines?.map((line, index) => (
              <section className="panel" key={`${line.component_label || line.component_name}-${index}`} style={{ marginTop: 14 }}>
                <div className="panel-header">
                  <div>
                    <div className="panel-title">
                      {line.component_name || line.component_label}
                      {line.material ? ` · ${line.material}` : ''}
                    </div>
                    <div className="panel-sub">{line.process === 'Kappa' ? 'Base Material' : line.process}</div>
                  </div>
                </div>
                <div className="component-process-results">
                  <CalcTracePanel rows={line.trace.map(item => ({ label: item.label, value: item.value }))} formula={line.formula} />
                  <div style={{ background: 'var(--line-2)', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 10, alignSelf: 'start' }}>
                    <div className="line-item">
                      <span>Total Cost</span>
                      <strong style={{ fontFamily: 'Manrope', fontSize: 15 }}>{money(line.total_cost)}</strong>
                    </div>
                    <div className="line-item">
                      <span>Cost / Box</span>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
                        <strong style={{ fontFamily: 'Manrope', fontSize: 15, color: 'var(--orange)' }}>{money(line.cost_per_box)}</strong>
                        {line.unit_cost != null && (
                          <span style={{ color: 'var(--amazonite)', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap' }}>
                            {money(line.unit_cost)} / {line.unit_label}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="line-item">
                      <span>Weightage</span>
                      <strong>{line.weightage_percent == null ? '—' : `${line.weightage_percent.toFixed(1)}%`}</strong>
                    </div>
                    <div style={{ borderTop: '1px solid var(--line)', paddingTop: 8, fontSize: 11 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <strong>{line.component_label}</strong>
                        <span>{money(line.total_cost)}</span>
                      </div>
                      <div style={{ color: 'var(--muted-2)', marginTop: 3 }}>
                        {line.process} · {line.weightage_percent?.toFixed(1) ?? '—'}% of estimate
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            ))}
            {componentCalculation?.module === module
              && !calculatingComponent
              && !componentCalculation.error
              && !componentCalculation.lines?.length
              && !componentCalculation.failures?.length && (
              <div className="info-banner" style={{ marginTop: 14 }}>No {moduleLabel} components are available to calculate.</div>
            )}
            <div className="modal-footer">
              <button className="btn btn-secondary" type="button" onClick={() => onCloseCalculationDetails?.()}>Close</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}