import React from 'react';

export const PROCESS_COLUMNS = [
  'Base Material', 'Wrapper', 'Printing', 'Lamination', 'Punching', 'Die Cutting',
  'Glue', 'Foiling', 'Spot UV', 'Drip-Off', 'Embossing', 'Debossing',
  'Accessories', 'Insert', 'Conversion', 'EB', 'One Time Cost',
];

export const MODULE_PROCESS_COLUMNS = {
  Kappa: ['Base Material'],
  Wrapper: ['Wrapper'],
  Printing: ['Printing'],
  Lamination: ['Lamination'],
  Punching: ['Punching', 'Die Cutting'],
  Glue: ['Glue'],
  Embellishments: ['Foiling', 'Spot UV', 'Drip-Off', 'Embossing', 'Debossing'],
  Accessories: ['Accessories'],
  Insert: ['Insert'],
  Conversion: ['Conversion'],
  EB: ['EB'],
  'One Time Cost': ['One Time Cost'],
};

export function componentsForModule(components = [], module) {
  const processes = MODULE_PROCESS_COLUMNS[module] || [];
  return components.filter(component => processes.some(process => component.processes?.[process] === true));
}

export default function ComponentProcessMatrix({
  components = [],
  onChange,
  editable = true,
  title = 'Component–Process Matrix',
}) {
  const updateComponent = (index, patch) => {
    onChange?.(components.map((component, rowIndex) => rowIndex === index ? { ...component, ...patch } : component));
  };

  const toggleProcess = (index, process) => {
    const component = components[index];
    const current = component.processes?.[process];
    updateComponent(index, {
      processes: { ...component.processes, [process]: current == null ? true : current === true ? false : null },
    });
  };

  const updateTooling = (index, key, value) => {
    const component = components[index];
    const processInputs = component.process_inputs || {};
    const tooling = processInputs['One Time Cost'] || {};
    updateComponent(index, {
      process_inputs: {
        ...processInputs,
        'One Time Cost': { ...tooling, [key]: value },
      },
    });
  };

  const addComponent = () => onChange?.([
    ...components,
    { component_name: '', material: '', source: 'manual', processes: {}, process_inputs: {} },
  ]);

  const removeComponent = index => onChange?.(components.filter((_, rowIndex) => rowIndex !== index));

  return (
    <section className="panel" style={{ padding: 0, overflow: 'hidden', marginBottom: 0 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h2 className="panel-title" style={{ marginBottom: 4 }}>{title}</h2>
          <p className="panel-sub">YES routes this component into the process. NO excludes it. REVIEW requires confirmation.</p>
        </div>
        {editable && <button className="btn btn-secondary btn-sm" type="button" onClick={addComponent}>Add Component</button>}
      </div>
      <div style={{ overflowX: 'auto', maxHeight: 430 }}>
        <table style={{ minWidth: 1500, borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead>
            <tr>
              <th style={{ position: 'sticky', left: 0, zIndex: 3, minWidth: 180, background: 'var(--panel)' }}>Component Name</th>
              <th style={{ position: 'sticky', left: 180, zIndex: 3, minWidth: 150, background: 'var(--panel)' }}>Material</th>
              {PROCESS_COLUMNS.map(process => <th key={process} style={{ textAlign: 'center', minWidth: 90 }}>{process}</th>)}
              <th style={{ minWidth: 250 }}>Tooling / Die Details</th>
              {editable && <th style={{ position: 'sticky', right: 0, zIndex: 3, background: 'var(--panel)' }}>Action</th>}
            </tr>
          </thead>
          <tbody>
            {components.map((component, index) => (
              <tr key={`${component.component_name}|${component.material}|${index}`}>
                <td style={{ position: 'sticky', left: 0, zIndex: 1, background: 'var(--panel)' }}>
                  {editable ? (
                    <input className="form-input" aria-label={`Component name row ${index + 1}`} value={component.component_name} onChange={event => updateComponent(index, { component_name: event.target.value })} />
                  ) : <strong>{component.component_name}</strong>}
                </td>
                <td style={{ position: 'sticky', left: 180, zIndex: 1, background: 'var(--panel)' }}>
                  {editable ? (
                    <input className="form-input" aria-label={`Material row ${index + 1}`} value={component.material} onChange={event => updateComponent(index, { material: event.target.value })} />
                  ) : component.material}
                </td>
                {PROCESS_COLUMNS.map(process => {
                  const value = component.processes?.[process];
                  const enabled = value === true;
                  const reviewRequired = value == null;
                  return (
                    <td key={process} style={{ textAlign: 'center' }}>
                      {editable ? (
                        <button
                          type="button"
                          className={`btn btn-sm ${enabled ? 'btn-primary' : 'btn-secondary'}`}
                          aria-label={`${component.component_name || `Component ${index + 1}`} ${process}: ${reviewRequired ? 'REVIEW REQUIRED' : enabled ? 'YES' : 'NO'}`}
                          aria-pressed={enabled}
                          onClick={() => toggleProcess(index, process)}
                          style={{
                            minWidth: 48, padding: '4px 7px',
                            ...(reviewRequired ? { background: '#FFF3DC', color: '#B47A20', borderColor: '#E8C98A' } : {}),
                          }}
                        >
                          {reviewRequired ? 'REVIEW' : enabled ? 'YES' : 'NO'}
                        </button>
                      ) : <span className={reviewRequired ? 'pill pill-required' : enabled ? 'pill pill-confirmed' : 'pill'}>{reviewRequired ? 'REVIEW' : enabled ? 'YES' : 'NO'}</span>}
                    </td>
                  );
                })}
                <td style={{ minWidth: 250 }}>
                  {component.processes?.['One Time Cost'] === true ? (() => {
                    const tooling = component.process_inputs?.['One Time Cost'] || {};
                    return editable ? (
                      <div style={{ display: 'grid', gap: 6 }}>
                        <select className="form-select" aria-label={`Tooling type for ${component.component_name}`} value={tooling.tooling_type || ''} onChange={event => updateTooling(index, 'tooling_type', event.target.value)}>
                          <option value="">Select die type</option>
                          <option value="Punching Die">Punching Die</option>
                          <option value="Emboss/Deboss Die">Emboss/Deboss Die</option>
                          <option value="Foil Stamp Die">Foil Stamp Die</option>
                        </select>
                        {tooling.tooling_type === 'Punching Die' ? (
                          <select className="form-select" aria-label={`Punching die sheet size for ${component.component_name}`} value={tooling.sheet_size || ''} onChange={event => updateTooling(index, 'sheet_size', event.target.value)}>
                            <option value="">Select sheet size</option>
                            {['15x20', '20x14', '20x28', '25x36', '28x40'].map(size => <option key={size} value={size}>{size}</option>)}
                          </select>
                        ) : ['Emboss/Deboss Die', 'Foil Stamp Die'].includes(tooling.tooling_type) ? (
                          <input className="form-input" type="number" min="0" step="any" aria-label={`Die area in square centimetres for ${component.component_name}`} placeholder="Area (sq.cm)" value={tooling.area_sq_cm ?? ''} onChange={event => updateTooling(index, 'area_sq_cm', event.target.value === '' ? '' : Number(event.target.value))} />
                        ) : null}
                      </div>
                    ) : <span>{tooling.tooling_type || 'Not configured'}{tooling.sheet_size ? ` · ${tooling.sheet_size}` : ''}{tooling.area_sq_cm != null ? ` · ${tooling.area_sq_cm} sq.cm` : ''}</span>;
                  })() : <span style={{ color: 'var(--muted-2)' }}>—</span>}
                </td>
                {editable && (
                  <td style={{ position: 'sticky', right: 0, zIndex: 1, background: 'var(--panel)', textAlign: 'center' }}>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => removeComponent(index)} aria-label={`Remove ${component.component_name || `component ${index + 1}`}`}>Remove</button>
                  </td>
                )}
              </tr>
            ))}
            {!components.length && (
              <tr><td colSpan={PROCESS_COLUMNS.length + 3 + Number(editable)} style={{ textAlign: 'center', padding: 28, color: 'var(--muted-2)' }}>No components are available. Add a component and explicitly mark its applicable processes YES.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}