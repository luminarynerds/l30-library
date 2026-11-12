/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Laptop, Wifi, Camera, Tablet, Gamepad2, Telescope, Microscope, Hammer, Box } from 'lucide-react'
import { type EquipmentType } from '../../api/equipment-api'

export function getEquipmentIcon(type: EquipmentType | null) {
  const iconClass = "w-5 h-5"
  switch (type) {
    case 'laptop': return <Laptop className={iconClass} />
    case 'hotspot': return <Wifi className={iconClass} />
    case 'camera': return <Camera className={iconClass} />
    case 'tablet': return <Tablet className={iconClass} />
    case 'gaming_console': return <Gamepad2 className={iconClass} />
    case 'telescope': return <Telescope className={iconClass} />
    case 'microscope': return <Microscope className={iconClass} />
    case 'tools': return <Hammer className={iconClass} />
    default: return <Box className={iconClass} />
  }
}
