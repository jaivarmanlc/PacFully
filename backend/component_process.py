"""Shared component/process routing rules for estimate calculations."""

PROCESS_TO_MODULE = {
    "Base Material": "Kappa",
    "Kappa": "Kappa",
    "Wrapper": "Wrapper",
    "Printing": "Printing",
    "Lamination": "Lamination",
    "Punching": "Punching",
    "Die Cutting": "Punching",
    "Glue": "Glue",
    "Foiling": "Embellishments",
    "Spot UV": "Embellishments",
    "Drip-Off": "Embellishments",
    "Embossing": "Embellishments",
    "Debossing": "Embellishments",
    "Accessories": "Accessories",
    "Insert": "Insert",
    "Conversion": "Conversion",
    "EB": "EB",
    "One Time Cost": "One Time Cost",
}


def component_label(component):
    """Return the user-facing component identity without requiring an ID."""
    return f"{component['component_name']}_{component['material']}"


def components_for_process(components, process):
    """Return only components whose central matrix marks a process YES."""
    if process not in PROCESS_TO_MODULE:
        raise ValueError(f"Unknown component process: {process}")
    return [
        component
        for component in components
        if (
            component.get("processes", {}).get(process) is True
            if isinstance(component, dict)
            else getattr(component, "processes", {}).get(process) is True
        )
    ]


def processes_for_module(module):
    """Return matrix columns that route into a costing module."""
    return tuple(
        process
        for process, target_module in PROCESS_TO_MODULE.items()
        if target_module == module
    )


def components_for_module(components, module):
    """Return components routed to a module by one or more YES values."""
    applicable_processes = set(processes_for_module(module))
    return [
        component
        for component in components
        if any(
            (
                component.get("processes", {}).get(process) is True
                if isinstance(component, dict)
                else getattr(component, "processes", {}).get(process) is True
            )
            for process in applicable_processes
        )
    ]