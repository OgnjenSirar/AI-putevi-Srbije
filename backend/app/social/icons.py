"""Jednostavne SVG ikonice za sablone (bez spoljnih zavisnosti)."""

_S = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"'

ICONS = {
    "radovi": f'<svg {_S}><path d="M26 10h12l12 42H14z" fill="currentColor" stroke="none"/><path d="M21 30h22M18 41h28" stroke="#FFB000" stroke-width="5"/><path d="M8 54h48"/></svg>',
    "zatvaranje": f'<svg {_S}><circle cx="32" cy="32" r="22"/><path d="M18 32h28" stroke-width="7"/></svg>',
    "obilazak": f'<svg {_S}><path d="M20 54V30a10 10 0 0 1 10-10h18"/><path d="M40 12l8 8-8 8"/></svg>',
    "upozorenje": f'<svg {_S}><path d="M32 8 58 54H6z"/><path d="M32 26v12"/><circle cx="32" cy="46" r="1.5" fill="currentColor"/></svg>',
    "info": f'<svg {_S}><circle cx="32" cy="32" r="22"/><path d="M32 30v14"/><circle cx="32" cy="21" r="1.5" fill="currentColor"/></svg>',
    "vreme": f'<svg {_S}><path d="M18 40a10 10 0 0 1 2-20 14 14 0 0 1 27 4 8 8 0 0 1-1 16z"/><path d="M24 48l-3 6M34 48l-3 6M44 48l-3 6"/></svg>',
    "tag": f'<svg {_S}><rect x="10" y="18" width="44" height="28" rx="6"/><path d="M20 32h10M38 26c4 3 4 9 0 12M44 22c7 6 7 14 0 20"/></svg>',
    "praznik": f'<svg {_S}><path d="M32 8l6 14 15 1-12 10 4 15-13-8-13 8 4-15-12-10 15-1z"/></svg>',
}

DEFAULT_ICON = {"radovi": "radovi", "obavestenje": "upozorenje", "naplata": "tag", "praznik": "praznik"}
