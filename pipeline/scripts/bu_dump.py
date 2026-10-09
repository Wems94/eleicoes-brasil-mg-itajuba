# Decodificador de referência de Boletim de Urna (ASN.1 BER do TSE).
# Uso: python bu_dump.py <arquivo.bu|.dat>
# Estrutura: envelope -> EntidadeBoletimUrna -> resultadosVotacaoPorEleicao -> cargos -> votos.
import sys
d=open(sys.argv[1],'rb').read()
def parse(b,i=0,end=None):
    end=len(b) if end is None else end; out=[]
    while i<end:
        t=b[i];i+=1;tn=t&0x1f
        l=b[i];i+=1
        if l&0x80:n=l&0x7f;l=int.from_bytes(b[i:i+n],'big');i+=n
        v=b[i:i+l]
        out.append((t,parse(b,i,i+l) if t&0x20 else v));i+=l
    return out
I=lambda v:int.from_bytes(v,'big',signed=True)
outer=parse(d)[0][1]
bu=parse(outer[4][1])[0][1]
for k,(t,v) in enumerate(bu): print(k,hex(t),v if not isinstance(v,list) else '...')
cargos={1:'Presidente',3:'Governador',5:'Senador',6:'Deputado Federal',7:'Deputado Estadual',8:'Deputado Distrital',2:'Vice-Presidente',4:'Vice-Governador'}
tipos={1:'nominal',2:'branco',3:'nulo',4:'legenda',5:'cargo sem candidato',6:'nominal anulado',7:'legenda anulado'}
res=bu[8][1]
for el in res:
    f=el[1]; print('\n=== Eleição',I(f[0][1]),'| aptos',I(f[1][1]),'|',I(f[2][1]),'|',I(f[3][1]))
    for rv in f[4][1]:
        r=rv[1]; print(' tipoCargo',I(r[0][1]),'comparecimento',I(r[1][1]))
        for tc in r[2][1]:
            c=tc[1]; cargo=I(c[0][1]); tot=0
            print('  --',cargos.get(cargo,cargo),'(ordem',I(c[1][1]),')')
            for vv in c[2][1]:
                x={t&0x1f:(val) for t,val in vv[1] if t&0xc0==0x80}
                tv=I(x[1]);q=I(x[2]);tot+=q
                if 3 in x: p=I(x[3][0][1]);n=I(x[3][1][1]);s=f'{n} (partido {p})'
                else: s=''
                print(f'     {tipos.get(tv,tv):10} {s:28} {q}')
            print('     TOTAL',tot)
