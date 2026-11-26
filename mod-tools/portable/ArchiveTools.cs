using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

public static class GoldMinerArchive {
    sealed class Entry {
        public string Name; public Dictionary<string,object> Node;
        public long Offset, Size; public bool Unpacked;
    }
    static JavaScriptSerializer Json() {
        return new JavaScriptSerializer { MaxJsonLength = int.MaxValue, RecursionLimit = 256 };
    }
    static Dictionary<string,object> Header(string path, out long start) {
        using (var f = File.OpenRead(path)) using (var r = new BinaryReader(f)) {
            if (r.ReadUInt32() != 4) throw new InvalidDataException("Invalid ASAR header.");
            uint span = r.ReadUInt32(); r.ReadUInt32(); uint length = r.ReadUInt32();
            if (span < 8 || length > span - 8 || 8L + span > f.Length)
                throw new InvalidDataException("Invalid ASAR header bounds.");
            start = 8L + span;
            return Json().Deserialize<Dictionary<string,object>>(Encoding.UTF8.GetString(r.ReadBytes((int)length)));
        }
    }
    static IEnumerable<Entry> Entries(Dictionary<string,object> node, string prefix) {
        var files = (Dictionary<string,object>)node["files"];
        foreach (var pair in files) {
            var item = (Dictionary<string,object>)pair.Value;
            string name = prefix + pair.Key;
            if (item.ContainsKey("files")) {
                foreach (var child in Entries(item, name + "/")) yield return child;
            } else if (!item.ContainsKey("link")) {
                bool unpacked = item.ContainsKey("unpacked") && Convert.ToBoolean(item["unpacked"]);
                yield return new Entry { Name=name, Node=item, Unpacked=unpacked,
                    Size=Convert.ToInt64(item["size"]),
                    Offset=unpacked ? 0 : Convert.ToInt64(item["offset"]) };
            }
        }
    }
    public static byte[] ReadFile(string archive, string name) {
        long start; var header = Header(archive, out start);
        foreach (var item in Entries(header, "")) if (item.Name == name) {
            if (item.Unpacked) return File.ReadAllBytes(Path.Combine(archive + ".unpacked", name.Replace('/', Path.DirectorySeparatorChar)));
            using (var f=File.OpenRead(archive)) {
                if (item.Size > int.MaxValue || item.Offset < 0 || start + item.Offset + item.Size > f.Length)
                    throw new InvalidDataException("Invalid ASAR entry bounds.");
                f.Position=start+item.Offset;
                var bytes=new byte[(int)item.Size]; int pos=0;
                while(pos<bytes.Length) { int n=f.Read(bytes,pos,bytes.Length-pos); if(n==0) throw new EndOfStreamException(); pos+=n; }
                return bytes;
            }
        }
        throw new FileNotFoundException("Required archive entry not found: " + name);
    }
    static string Hash(byte[] bytes) {
        using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
    static void Copy(Stream source, Stream dest, long count) {
        byte[] buffer=new byte[1024*1024];
        while(count>0) { int n=source.Read(buffer,0,(int)Math.Min(count,buffer.Length)); if(n==0) throw new EndOfStreamException(); dest.Write(buffer,0,n); count-=n; }
    }
    public static void Patch(string source, string target, Dictionary<string,byte[]> replacements) {
        long start; var header=Header(source,out start); var items=new List<Entry>(Entries(header,""));
        var remaining=new HashSet<string>(replacements.Keys); long offset=0;
        foreach(var item in items) {
            byte[] bytes;
            if(replacements.TryGetValue(item.Name,out bytes)) {
                remaining.Remove(item.Name); item.Node.Remove("unpacked");
                item.Node["size"]=bytes.Length;
                int blockSize=4194304; var blocks=new List<string>();
                for(int i=0;i<bytes.Length;i+=blockSize) {
                    var block=new byte[Math.Min(blockSize,bytes.Length-i)]; Array.Copy(bytes,i,block,0,block.Length); blocks.Add(Hash(block));
                }
                item.Node["integrity"]=new Dictionary<string,object> { {"algorithm","SHA256"}, {"hash",Hash(bytes)}, {"blockSize",blockSize}, {"blocks",blocks} };
                item.Node["offset"]=offset.ToString(); offset+=bytes.Length;
            } else if(!item.Unpacked) { item.Node["offset"]=offset.ToString(); offset+=item.Size; }
        }
        if(remaining.Count>0) throw new InvalidDataException("A required archive entry is missing.");
        byte[] encoded=Encoding.UTF8.GetBytes(Json().Serialize(header)); int padding=(4-encoded.Length%4)%4;
        using(var input=File.OpenRead(source)) using(var output=File.Create(target)) using(var writer=new BinaryWriter(output)) {
            writer.Write(4); writer.Write(8+encoded.Length+padding); writer.Write(4+encoded.Length+padding); writer.Write(encoded.Length);
            writer.Write(encoded); writer.Write(new byte[padding]);
            foreach(var item in items) {
                byte[] bytes;
                if(replacements.TryGetValue(item.Name,out bytes)) writer.Write(bytes);
                else if(!item.Unpacked) {
                    if(item.Offset<0 || start+item.Offset+item.Size>input.Length) throw new InvalidDataException("Invalid ASAR source range.");
                    input.Position=start+item.Offset; Copy(input,output,item.Size);
                }
            }
        }
    }
    const string Begin="/* GOLDMINER_COOP_HASHES_BEGIN */";
    const string Data="/* GOLDMINER_COOP_HASHES_DATA */";
    const string End="/* GOLDMINER_COOP_HASHES_END */";
    static int ExpressionEnd(string text,int start) {
        int depth=0; char quote='\0';
        for(int i=start;i<text.Length;i++) {
            char c=text[i];
            if(quote!='\0') { if(c=='\\') i++; else if(c==quote) quote='\0'; continue; }
            if(c=='\'' || c=='"' || c=='`') { quote=c; continue; }
            if(c=='/' && i+1<text.Length && text[i+1]=='*') { int end=text.IndexOf("*/",i+2,StringComparison.Ordinal); if(end<0) throw new InvalidDataException("Unclosed comment."); i=end+1; continue; }
            if(c=='(' || c=='[' || c=='{') depth++;
            else if(c==')' || c==']' || c=='}') depth--;
            else if(depth==0 && (c==',' || c==';')) return i;
        }
        throw new InvalidDataException("Could not locate the resource hash expression.");
    }
    public static string RemoveHashes(string text) {
        int start=text.IndexOf(Begin,StringComparison.Ordinal); if(start<0) return text;
        int data=text.IndexOf("),"+Data,start,StringComparison.Ordinal);
        int end=text.IndexOf(End,start,StringComparison.Ordinal);
        string prefix=Begin+"Object.assign((";
        if(data<0 || end<data || text.Substring(start,prefix.Length)!=prefix) throw new InvalidDataException("Unrecognized co-op hash wrapper.");
        string original=text.Substring(start+prefix.Length,data-start-prefix.Length);
        return text.Substring(0,start)+original+text.Substring(end+End.Length);
    }
    public static string SetHashes(string text,string hashes) {
        text=RemoveHashes(text);
        var match=System.Text.RegularExpressions.Regex.Match(text,@"\bSWF_SHA_BAKED\s*=");
        if(!match.Success) throw new InvalidDataException("This launcher does not expose the expected SWF hash table. Use loose rf.swf installation if available.");
        int start=match.Index+match.Length, end=ExpressionEnd(text,start);
        return text.Substring(0,start)+Begin+"Object.assign(("+text.Substring(start,end-start)+"),"+Data+hashes+")"+End+text.Substring(end);
    }
}
