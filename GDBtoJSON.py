import struct
import io
import json
import sys

def ReadNullTerminatedString(fObj):
    bytesContainer = b''
    while True:
        b = fObj.read(1)
        if b != b"\x00":
            bytesContainer += b
        else:
            return bytesContainer.decode("ASCII")
            

TypeToName = ["GDB", "Array", "Type2", "Bool", "Float", "Int", "Matrix", "Node", "Type8", "String", "Type10", "Vector2", "Vector3", "Vector4", "Colour", "UInt"]

DepthOffsets = [12]
DepthValues = [0]
AddEndQueue = []
AllEntries = []
GDBEntries = []
NodeEntries = []
VariableEntries = []
EntryOffsets = []
EntryParents = []  # Entry parent struct: Type, Index.
file = sys.argv[1]

with open(file, 'rb') as f:
    with open(f"{file}.json", 'w') as o:
        Magic = f.read(4)
        Nulls = f.read(4)
        VariableNameTableOffset = struct.unpack("i", f.read(4))[0]
        # Get this sorted first
        f.seek(VariableNameTableOffset)
        NameTableLength = struct.unpack("i", f.read(4))[0]
        NameTableBytes = io.BytesIO(f.read(NameTableLength))
        f.seek(12)  # to return to the real data.
        PrevDepth = 0
        while f.tell() < VariableNameTableOffset:  # since the name table offset marks the end of the data.
            Entry = {}
            EntryDepthIndex = DepthOffsets.index(f.tell())
            CurrentDepth = DepthValues[EntryDepthIndex]
            try:
                EntryParentIndex = EntryOffsets.index(f.tell())
            except:
                EntryParentIndex = None  # doesn't exist
            EntryDataType = struct.unpack("B", f.read(1))[0]
            EntryDataCount = struct.unpack("B", f.read(1))[0]  # 0 if it isn't a GDB or Node
            Reserved = f.read(2)
            VariableNameOffset = struct.unpack("i", f.read(4))[0]
            NameTableBytes.seek(VariableNameOffset)
            VariableName = ReadNullTerminatedString(NameTableBytes)
            Entry["Type"] = TypeToName[EntryDataType]
            Entry["Name"] = VariableName
            print(f"{TypeToName[EntryDataType]} {VariableName} // Depth = {CurrentDepth}")
            Entry["Depth"] = CurrentDepth
            VariableHash = f.read(4)
            if EntryDataType == 0:  # GDB, contains a list of offsets to variables.
                Entry["GDBVariableOffsets"] = []
                Entry["Children"] = []
                for i in range(EntryDataCount):
                    off = struct.unpack("i", f.read(4))[0]
                    Entry["GDBVariableOffsets"].append(off)
                    DepthOffsets.append(off)
                    DepthValues.append(CurrentDepth + 1)  # increased depth by one for each subentry in a gdb
                    EntryOffsets.append(off)
                    EntryParents.append(["GDB", len(GDBEntries)]) # since we're adding it to the list here too, the length equals the index of this item. the GDB tells us where to look
                GDBEntries.append(Entry)
                # Try to parent correctly (though a gdb shouldn't be parented to anything else)
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 1:  # Array
                ArraySize = struct.unpack("i", f.read(4))[0]
                ArrayDataType = struct.unpack("i", f.read(4))[0]
                Entry["ArrayValues"] = []
                if ArrayDataType == 3:
                    for i in range(ArraySize):
                        Entry["ArrayValues"].append(bool(struct.unpack("b", f.read(1))[0]))
                        while f.tell() % 4 != 0:
                            f.seek(1, 1)  # align
                if ArrayDataType == 4:
                    for i in range(ArraySize):
                        Entry["ArrayValues"].append(struct.unpack("f", f.read(4))[0])
                if ArrayDataType == 5:
                    for i in range(ArraySize):
                        Entry["ArrayValues"].append(struct.unpack("i", f.read(4))[0])
                if ArrayDataType == 15:
                    print(f.tell())
                    for i in range(ArraySize):
                        Entry["ArrayValues"].append(struct.unpack("I", f.read(4))[0])
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 3:
                Entry["BooleanValue"] = bool(struct.unpack("i", f.read(4))[0])
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 4:
                Entry["FloatValue"] = struct.unpack("f", f.read(4))[0]
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 5:
                Entry["IntegerValue"] = struct.unpack("i", f.read(4))[0]
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 6:
                Entry["Matrix"] = [struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16))]
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 7:
                Entry["NodeVariableOffsets"] = []
                Entry["Children"] = []
                for i in range(EntryDataCount):
                    off = struct.unpack("i", f.read(4))[0]
                    Entry["NodeVariableOffsets"].append(off)
                    DepthOffsets.append(off)
                    DepthValues.append(CurrentDepth + 1)  # increased depth by one for each subentry in a gdb
                    EntryOffsets.append(off)
                    EntryParents.append(["Node", len(NodeEntries)]) # since we're adding it to the list here too, the length equals the index of this item. the GDB tells us where to look
                # We can't actually parent the nodes themselves yet, so do the next best thing
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    Entry["TempParentType"] = ParentItem[0]
                    Entry["TempParentIdx"] = ParentItem[1]
                NodeEntries.append(Entry)
            elif EntryDataType == 9:
                StrDataLengthUnneeded = f.read(4)
                Entry["String"] = ReadNullTerminatedString(f)
                while f.tell() % 4 != 0:
                    f.seek(1, 1) # align
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 11:
                Entry["Vec2"] = struct.unpack("ff", f.read(8))
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 12:
                Entry["Vec3"] = struct.unpack("fff", f.read(12))
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 13:
                Entry["Vec4"] = struct.unpack("ffff", f.read(16))
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 14:
                Entry["Colour"] = struct.unpack("BBBB", f.read(4))
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            elif EntryDataType == 15:
                Entry["UnsignedIntegerValue"] = struct.unpack("I", f.read(4))[0]
                # Try to parent correctly
                if EntryParentIndex != None:
                    ParentItem = EntryParents[EntryParentIndex]
                    if ParentItem[0] == "GDB":  # never should be, but you never know
                        GDBEntries[ParentItem[1]]["Children"].append(Entry)
                    elif ParentItem[0] == "Node":  # never should be, but you never know
                        NodeEntries[ParentItem[1]]["Children"].append(Entry)
            PrevDepth = CurrentDepth
        # Now a roundabout way of parenting the nodes to each other.
        secondary = NodeEntries
        for index, item in enumerate(secondary):
            # Get Parent type
            newItem = item
            # some modifications to clean this up
            
            PT = newItem["TempParentType"]  # because apparently newItem = item means newItem affects item
            PI = newItem["TempParentIdx"]  # because apparently newItem = item means newItem affects item
            newItem.pop("TempParentType")
            newItem.pop("TempParentIdx")
            newItem.pop("NodeVariableOffsets")
            if PT == "GDB":
                GDBEntries[PI]["Children"].append(newItem)
            elif PT == "Node":
                NodeEntries[PI]["Children"].append(newItem)
        GDBEntries[0].pop("GDBVariableOffsets")
        json.dump({"GDJ1": GDBEntries[0]}, o, indent=2)
            
                
                
            
                
                        
                
            
            