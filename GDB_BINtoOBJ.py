import struct
import io
import json
import sys

def FaceStrGen(indices, BaseIndex, UseNormal, UseTexcoord):
    print(UseNormal)
    print(UseTexcoord)
    f1Base = f"{indices[0]+1 + BaseIndex}"
    f2Base = f"{indices[1]+1 + BaseIndex}"
    f3Base = f"{indices[2]+1 + BaseIndex}"
    if UseTexcoord and UseNormal:
        f1Base += f"/{indices[0]+1 + BaseIndex}/{indices[0]+1 + BaseIndex}"
        f2Base += f"/{indices[1]+1 + BaseIndex}/{indices[1]+1 + BaseIndex}"
        f3Base += f"/{indices[2]+1 + BaseIndex}/{indices[2]+1 + BaseIndex}"
    else:
        if UseTexcoord:
            f1Base += f"/{indices[0]+1 + BaseIndex}"
            f2Base += f"/{indices[1]+1 + BaseIndex}"
            f3Base += f"/{indices[2]+1 + BaseIndex}"
        else:
            if UseNormal:
                f1Base += f"//{indices[0]+1 + BaseIndex}"
                f2Base += f"//{indices[1]+1 + BaseIndex}"
                f3Base += f"//{indices[2]+1 + BaseIndex}"
            else:
                f1Base += ''
                f2Base += ''
                f3Base += ''
    return f"f {f1Base} {f2Base} {f3Base}\n"

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
            Entry["Data"] = []
            Entry["Children"] = []
            for i in range(EntryDataCount):
                off = struct.unpack("i", f.read(4))[0]
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
            Entry["Data"] = []
            if ArrayDataType == 3:
                for i in range(ArraySize):
                    Entry["Data"].append(bool(struct.unpack("b", f.read(1))[0]))
                    while f.tell() % 4 != 0:
                        f.seek(1, 1)  # align
            if ArrayDataType == 4:
                for i in range(ArraySize):
                    Entry["Data"].append(struct.unpack("f", f.read(4))[0])
            if ArrayDataType == 5:
                for i in range(ArraySize):
                    Entry["Data"].append(struct.unpack("i", f.read(4))[0])
            if ArrayDataType == 15:
                print(f.tell())
                for i in range(ArraySize):
                    Entry["Data"].append(struct.unpack("I", f.read(4))[0])
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 3:
            Entry["Data"] = bool(struct.unpack("i", f.read(4))[0])
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 4:
            Entry["Data"] = struct.unpack("f", f.read(4))[0]
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 5:
            Entry["Data"] = struct.unpack("i", f.read(4))[0]
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 6:
            Entry["Data"] = [struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16)), struct.unpack("ffff", f.read(16))]
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 7:
            Entry["Data"] = []
            Entry["Children"] = []
            for i in range(EntryDataCount):
                off = struct.unpack("i", f.read(4))[0]
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
            Entry["Data"] = ReadNullTerminatedString(f)
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
            Entry["Data"] = struct.unpack("ff", f.read(8))
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 12:
            Entry["Data"] = struct.unpack("fff", f.read(12))
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 13:
            Entry["Data"] = struct.unpack("ffff", f.read(16))
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 14:
            Entry["Data"] = struct.unpack("BBBB", f.read(4))
            # Try to parent correctly
            if EntryParentIndex != None:
                ParentItem = EntryParents[EntryParentIndex]
                if ParentItem[0] == "GDB":  # never should be, but you never know
                    GDBEntries[ParentItem[1]]["Children"].append(Entry)
                elif ParentItem[0] == "Node":  # never should be, but you never know
                    NodeEntries[ParentItem[1]]["Children"].append(Entry)
        elif EntryDataType == 15:
            Entry["Data"] = struct.unpack("I", f.read(4))[0]
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
        newItem.pop("Data")
        if PT == "GDB":
            GDBEntries[PI]["Children"].append(newItem)
        elif PT == "Node":
            NodeEntries[PI]["Children"].append(newItem)
    GDBEntries[0].pop("Data")
    GDBDict = {"GDJ1": GDBEntries[0]}
        
with open(file.split('.')[0] + ".modelbin", 'rb') as mdb:
    with open(file + ".obj", 'w') as obj:
        with open(file + ".mtl", 'w') as mtl:
            # Handle material list generation first
            MatList = []
            MatNode = None
            for Node in GDBDict["GDJ1"]["Children"]:
                if Node["Name"] == "Materials":
                    MatNode = Node
            if MatNode == None:
                print("Something went horrifically wrong...")  # make the user think something broke big time when really, they likely just used the wrong file.
                exit()
            
            for Mat in MatNode["Children"]:
                #Diffuse = [0, 0, 0, 0]
                #Ambient = [0, 0, 0, 0]
                #Specular = [0, 0, 0, 0]
                #Name = ""
                for Var in Mat["Children"]:
                    if Var['Type'] != "Node":
                        if Var['Type'] == "String":
                            exec(f"{Var['Name']} = '{Var['Data']}'")
                        else:
                            exec(f"{Var['Name']} = {Var['Data']}")
                mtl.write(f"newmtl {Name}\n")
                mtl.write(f"Kd {Diffuse[0] / 255} {Diffuse[1] / 255} {Diffuse[2] / 255}\n")
                mtl.write(f"Ka {Ambient[0] / 255} {Ambient[1] / 255} {Ambient[2] / 255}\n")
                mtl.write(f"Ks {Specular0[0] / 255} {Specular0[1] / 255} {Specular0[2] / 255}\n")
                MatList.append(Name)
            MeshIndex = 0
            BaseIndex = 0
            # Get the root geometry node
            GeoNode = None
            for Node in GDBDict["GDJ1"]["Children"]:
                if Node["Name"] == "Geometries":
                    GeoNode = Node
            # simple check here
            if GeoNode == None:
                print("No geometry, exiting")
                exit()
                
            for SubGeoNode in GeoNode["Children"]:
                PrimitiveType = -1
                VertexFormat = -1
                AttrScale0 = [0, 0, 0, 0]
                AttrScale1 = [0, 0, 0, 0]
                IndexFormat = -1
                IndexStreamOffset = -1
                IndexStreamSize = -1
                IndexNum = -1
                VertexStreamOffset = -1
                VertexStreamSize = -1
                VertexNum = -1
                MaterialIndex = -1
                for Var in SubGeoNode["Children"]:
                    # simplify this slightly
                    exec(f"{Var['Name']} = {Var['Data']}")
                # All of the above values are needed for a model to work correctly. as such this should now work 100% of the time
                # Proceed to read mesh data
                # First, Vertex data
                mdb.seek(VertexStreamOffset)
                # try to get the vertex format
                VFormatBits = format(VertexFormat, 'b').zfill(32)
                print(VFormatBits)
                VertexDataFlags = VFormatBits[24:32]  # f0 = pos, f1 = norm, f2 = col, f3 = texcoord0, f4 = tangent, f5 = texcoord1
                print(VertexDataFlags)
                bitfield1 = VFormatBits[16:24]
                VertexValueTypeFlags = VFormatBits[8:16]
                bitfield3 = VFormatBits[0:8]
                t = ''
                s = 0
                # inaccurate, but should work for now
                if VertexValueTypeFlags[4:] == '1111':
                    t = 'f'
                    s = 4
                else:
                    t = 'h'
                    s = 2
                    
                print(t, s)
                    
                UseNormal = bool(int(VertexDataFlags[6]))
                UseTexcoord = bool(int(VertexDataFlags[4]))
                
                # now read verts
                for i in range(VertexNum):
                    if VertexDataFlags[7] == '1':  # Pos
                        Position = struct.unpack('3' + t, mdb.read(s * 3))
                        obj.write(f"v {Position[0]/32768} {Position[1]/32768} {Position[2]/32768}\n")
                    if VertexDataFlags[6] == '1':  # Norm
                        Normal = struct.unpack('3' + t, mdb.read(s * 3))
                        obj.write(f"vn {Normal[0]/32768} {Normal[1]/32768} {Normal[2]/32768}\n")
                    if VertexDataFlags[5] == '1':  # Col
                        VertColor = struct.unpack('4B', mdb.read(4))
                    if VertexDataFlags[4] == '1':
                        TexCoord0 = struct.unpack('2' + t, mdb.read(s * 2))
                        obj.write(f"vt {TexCoord0[0]/32768} {TexCoord0[1]/32768}\n")
                    if VertexDataFlags[3] == '1':
                        Tangent = struct.unpack('3' + t, mdb.read(s * 2))
                    if VertexDataFlags[2] == '1':
                        TexCoord1 = struct.unpack('2' + t, mdb.read(s * 2))
                        
                # Indices
                mdb.seek(IndexStreamOffset)
                baseIndexGetList = []
                # since we're here
                obj.write(f"o Geometry_{MeshIndex}\n")
                obj.write(f"usemtl {MatList[MaterialIndex]}\n")
                FirstFace = struct.unpack('hhh', mdb.read(6))
                f2 = FirstFace[1]
                f3 = FirstFace[2]
                baseIndexGetList.append(FirstFace[0])
                baseIndexGetList.append(FirstFace[1])
                baseIndexGetList.append(FirstFace[2])
                FStr = FaceStrGen(FirstFace, BaseIndex, UseNormal, UseTexcoord)
                obj.write(FStr)
                for i in range(IndexNum - 3):
                    Face = [f2, f3]
                    nextFace = struct.unpack('h', mdb.read(2))[0]
                    Face.append(nextFace)
                    baseIndexGetList.append(nextFace)
                    f2 = f3
                    f3 = nextFace
                    FStr = FaceStrGen(Face, BaseIndex, UseNormal, UseTexcoord)
                    obj.write(FStr)
                MeshIndex += 1
                BaseIndex += max(baseIndexGetList)
                    
                
            
            
            
                
                
            
                
                        
                
            
            