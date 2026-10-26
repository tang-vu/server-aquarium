import csv,ctypes,datetime,io,json,math,platform,re,subprocess
from pathlib import Path

GPU_QUERY=['nvidia-smi','--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw','--format=csv,noheader,nounits']
WINDOWS_MEMORY_QUERY=['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command','$mem = Get-CimInstance Win32_OperatingSystem; @{totalBytes=([uint64]$mem.TotalVisibleMemorySize * 1024);availableBytes=([uint64]$mem.FreePhysicalMemory * 1024)} | ConvertTo-Json -Compress']

def number(value,limit=None):
    try:
        if isinstance(value,bool):return None
        n=float(value)
        return n if math.isfinite(n) and n>=0 and (limit is None or n<=limit) else None
    except (TypeError,ValueError):return None

def memory_amount(value):
    if not isinstance(value,str):return None
    match=re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KiB|MiB|GiB|TiB|kB|KB|MB|GB|TB)\s*',value)
    if not match:return None
    units={'B':1,'KiB':1024,'MiB':1024**2,'GiB':1024**3,'TiB':1024**4,'kB':1000,'KB':1000,'MB':1000**2,'GB':1000**3,'TB':1000**4}
    n=number(match[1])
    if n is None:return None
    result=n*units[match[2]]
    return int(result) if math.isfinite(result) else None

def memory_usage(value):
    if not isinstance(value,str) or value.count('/')!=1:return None,None
    left,right=value.split('/')
    return memory_amount(left),memory_amount(right)

def memory_record(total,available,label):
    total=number(total);available=number(available)
    if total is None or total<=0 or available is None or available>total:return None
    return dict(label=label,totalBytes=int(total),availableBytes=int(available),usedBytes=int(total-available),percent=(total-available)*100/total)

def linux_memory():
    fields={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('MemTotal','MemAvailable'):
            match=re.fullmatch(r'\s*(\d+)\s+kB\s*',value)
            if match:fields[key]=int(match[1])*1024
    return fields.get('MemTotal'),fields.get('MemAvailable')

def windows_memory():
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ['total','available','totalPageFile','availablePageFile','totalVirtual','availableVirtual','availableExtendedVirtual']]
    value=MemoryStatus();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):raise OSError('Memory reader unavailable')
    return value.total,value.available

def parse_gpus(text):
    output=[];ids=set()
    for row in csv.reader(io.StringIO(text)):
        if not row or not any(x.strip() for x in row):continue
        if len(row)!=7 or not re.fullmatch(r'\d+',row[0].strip()):raise ValueError('Invalid GPU sample')
        identity='gpu-'+row[0].strip()
        if identity in ids or len(output)>=16:raise ValueError('Invalid GPU identities')
        ids.add(identity)
        used,total=number(row[3]),number(row[4])
        used=int(used*1024**2) if used is not None else None
        total=int(total*1024**2) if total is not None and total>0 else None
        if used is not None and total is not None and used>total:used=None
        output.append(dict(id=identity,name=row[1].strip() or identity,utilization=number(row[2],100),memoryUsedBytes=used,memoryTotalBytes=total,temperatureC=number(row[5],200),powerW=number(row[6])))
    return output

def collect_hardware(runner=None,system=None,release=None,linux_reader=None,windows_reader=None):
    runner=runner or subprocess.run;system=system or platform.system()
    release=platform.release() if release is None else release
    linux_reader=linux_reader or linux_memory;windows_reader=windows_reader or windows_memory
    def run(argv):
        result=runner(argv,shell=False,capture_output=True,text=True,timeout=5)
        if result.returncode:raise RuntimeError('Reader unavailable')
        return result.stdout
    memory=None;runtime=None;warnings=[]
    wsl=system=='Linux' and 'microsoft' in release.lower()
    label='Windows host RAM' if system=='Windows' or wsl else 'Linux system RAM'
    try:
        if system=='Windows':memory=memory_record(*windows_reader(),label)
        elif system=='Linux':
            local=memory_record(*linux_reader(),'ODS WSL runtime RAM' if wsl else label)
            if wsl:runtime=local
            else:memory=local
        else:label='System RAM';warnings.append('System RAM reader unavailable on this platform.')
    except Exception:warnings.append('System RAM reader unavailable.')
    if wsl:
        try:
            values=json.loads(run(WINDOWS_MEMORY_QUERY))
            memory=memory_record(values.get('totalBytes'),values.get('availableBytes'),label)
        except Exception:warnings.append('Windows host RAM unavailable; WSL RAM is shown separately.')
    if memory is None and not warnings:warnings.append('System RAM values unavailable.')
    gpus=[];gpu_status='unavailable'
    try:
        gpus=parse_gpus(run(GPU_QUERY));gpu_status='ok' if gpus else 'no-nvidia-device'
    except Exception:warnings.append('NVIDIA GPU telemetry unavailable. Other GPU vendors are not measured by this reader.')
    return dict(source='system',sampledAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),memory=memory,memoryLabel=label,runtimeMemory=runtime,gpus=gpus,gpuStatus=gpu_status,warnings=warnings)
