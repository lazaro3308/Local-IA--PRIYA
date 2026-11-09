from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    IPictureDisp, OLE_YPOS_PIXELS, VgaColor, Default,
    OLE_YPOS_CONTAINER, DISPPARAMS, FONTITALIC, OLE_HANDLE, IDispatch,
    Gray, Color, OLE_XPOS_PIXELS, StdFont, Font, IEnumVARIANT,
    HRESULT, EXCEPINFO, OLE_CANCELBOOL, BSTR, IPicture, IFontDisp,
    FONTSIZE, OLE_XSIZE_CONTAINER, DISPPROPERTY, DISPMETHOD, Picture,
    OLE_YPOS_HIMETRIC, OLE_COLOR, dispid, Monochrome,
    FONTSTRIKETHROUGH, FONTBOLD, _lcid, OLE_XPOS_CONTAINER, CoClass,
    OLE_YSIZE_CONTAINER, VARIANT_BOOL, OLE_OPTEXCLUSIVE,
    OLE_XSIZE_HIMETRIC, FONTUNDERSCORE, OLE_YSIZE_PIXELS,
    _check_version, typelib_path, Unchecked, FONTNAME, COMMETHOD,
    OLE_YSIZE_HIMETRIC, IUnknown, OLE_XPOS_HIMETRIC, OLE_XSIZE_PIXELS,
    IFontEventsDisp, GUID, Library, FontEvents, OLE_ENABLEDEFAULTBOOL,
    StdPicture, Checked, IFont
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


__all__ = [
    'IPictureDisp', 'OLE_YPOS_PIXELS', 'Monochrome', 'VgaColor',
    'Default', 'FONTSTRIKETHROUGH', 'OLE_YPOS_CONTAINER', 'FONTBOLD',
    'OLE_XPOS_CONTAINER', 'OLE_YSIZE_CONTAINER', 'FONTITALIC',
    'OLE_OPTEXCLUSIVE', 'OLE_XSIZE_HIMETRIC', 'FONTUNDERSCORE',
    'OLE_HANDLE', 'OLE_YSIZE_PIXELS', 'Gray', 'typelib_path', 'Color',
    'Unchecked', 'FONTNAME', 'OLE_XPOS_PIXELS', 'StdFont', 'Picture',
    'Font', 'OLE_YSIZE_HIMETRIC', 'OLE_XPOS_HIMETRIC',
    'OLE_XSIZE_PIXELS', 'OLE_CANCELBOOL', 'IFontEventsDisp',
    'IPicture', 'IFontDisp', 'FONTSIZE', 'Library',
    'OLE_XSIZE_CONTAINER', 'OLE_TRISTATE', 'FontEvents',
    'OLE_ENABLEDEFAULTBOOL', 'StdPicture', 'LoadPictureConstants',
    'Checked', 'IFont', 'OLE_YPOS_HIMETRIC', 'OLE_COLOR'
]

