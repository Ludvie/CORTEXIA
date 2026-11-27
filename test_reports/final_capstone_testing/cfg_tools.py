"""Statement-level CFG and execution instrumentation of copied AST only.
Compound boolean expressions are atomic predicates. Comprehensions, ternaries,
called functions and nested function bodies are opaque at this abstraction level.
They remain covered separately by Python branch coverage and boundary cases.
"""
import ast, copy, inspect
from collections import Counter
from common import *

class CFG:
    def __init__(self, fn):
        self.fn=fn; self.nodes={};self.edges=[];self.marks={};self.traces=[]
        tree=ast.parse(inspect.getsource(fn));self.tree=tree;self.func=tree.body[0]
        self.offset=inspect.getsourcelines(fn)[1]-1
        self.entry=self.node('ENTRY',0);self.exit=self.node('EXIT',0)
        start=self.block(self.func.body,self.exit)
        self.edge(self.entry,start)
        self.predicates=sum(1 for n in self.nodes if sum(a==n for a,b,k in self.edges)>1)
        self.complexity=len(self.edges)-len(self.nodes)+2
        assert self.complexity==self.predicates+1
        clone=copy.deepcopy(tree)
        parent=self
        class Trace(ast.NodeTransformer):
            def visit_FunctionDef(self,node):
                if node.name!=fn.__name__: return node
                new=[]
                for s in node.body:new.extend(self.visit_statement(s))
                node.body=[parent.touch(parent.entry)]+new
                return node
            def visit_statement(self,s):
                ident=parent.marks[(s.lineno,s.col_offset)]
                if isinstance(s,ast.If):
                    s.test=parent.test(ident,s.test)
                    s.body=[n for x in s.body for n in self.visit_statement(x)]
                    s.orelse=[n for x in s.orelse for n in self.visit_statement(x)]
                    return [s]
                if isinstance(s,ast.While):
                    s.test=parent.test(ident,s.test)
                    s.body=[n for x in s.body for n in self.visit_statement(x)]
                    return [s]
                if isinstance(s,ast.For):
                    s.body=[parent.touch(ident)]+[n for x in s.body for n in self.visit_statement(x)]
                    return [s,parent.touch(ident)]
                return [parent.touch(ident),s]
        clone=Trace().visit(clone);ast.fix_missing_locations(clone)
        self.current=[]
        env=dict(fn.__globals__);env['_cfg_touch']=lambda n:self.current.append(n)
        exec(compile(clone,'<audit-copy:'+fn.__name__+'>','exec'),env)
        self.instrumented=env[fn.__name__]
    def node(self,label,line):
        i=len(self.nodes)+1;self.nodes[i]={'label':label,'line':line};return i
    def edge(self,a,b,label=''):self.edges.append((a,b,label))
    def block(self,stmts,nextnode,loop=None):
        for s in reversed(stmts):
            text=ast.unparse(s).splitlines()[0][:100]
            n=self.node(text,s.lineno+self.offset);self.marks[(s.lineno,s.col_offset)]=n
            if isinstance(s,ast.If):
                self.edge(n,self.block(s.body,nextnode,loop),'T');self.edge(n,self.block(s.orelse,nextnode,loop),'F')
            elif isinstance(s,(ast.For,ast.While)):
                self.edge(n,self.block(s.body,n,(n,nextnode)),'T');self.edge(n,nextnode,'F')
                assert not s.orelse, 'Loop else requires an explicit CFG extension'
            elif isinstance(s,ast.Continue):self.edge(n,loop[0])
            elif isinstance(s,ast.Break):self.edge(n,loop[1])
            elif isinstance(s,ast.Return):self.edge(n,self.exit)
            else:self.edge(n,nextnode)
            nextnode=n
        return nextnode
    def touch(self,n):return ast.Expr(ast.Call(ast.Name('_cfg_touch',ast.Load()),[ast.Constant(n)],[]))
    def test(self,n,expr):return ast.Subscript(ast.Tuple([self.touch(n).value,expr],ast.Load()),ast.Constant(1),ast.Load())
    def run(self,case_id,args,expected,project=lambda x:x):
        actual=self.fn(*args)
        self.current=[];copied=self.instrumented(*copy.deepcopy(args));self.current.append(self.exit)
        assert copied==actual, 'Instrumented AST changed behavior'
        pairs=list(zip(self.current,self.current[1:]))
        edges={(a,b) for a,b,_ in self.edges}
        assert all(e in edges for e in pairs),(case_id,[e for e in pairs if e not in edges])
        self.traces.append({'case_id':case_id,'nodes':list(self.current),'input':repr(args),'expected':expected,'actual':project(actual)})
        return actual
    def export(self):
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        name=self.fn.__name__;base='01_whitebox/'+name
        # IDs and source line labels keep large graphs legible; full statements in CSV.
        mermaid=['flowchart TD']+[f'  N{i}["N{i}: L{v["line"]}"]' for i,v in self.nodes.items()]
        mermaid += [f'  N{a} -->'+(f'|{k}|' if k else '')+f' N{b}' for a,b,k in self.edges]
        write(base+'.mmd','\n'.join(mermaid))
        csvout(base+'_nodes.csv',[{'node':i,**v} for i,v in self.nodes.items()])
        # Compact three-column graph with explicit numbered edges and readable labels.
        ids=sorted(self.nodes);pos={n:((n-1)%3, -((n-1)//3)) for n in ids}
        fig,ax=plt.subplots(figsize=(12,max(5,len(ids)/5)))
        for a,b,k in self.edges:
            x,y=pos[a];xx,yy=pos[b]
            ax.annotate('',xy=(xx,yy),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='#a5acc7',alpha=.55,connectionstyle='arc3,rad=.12',shrinkA=18,shrinkB=18))
            if k:ax.text((x+xx)/2,(y+yy)/2,k,fontsize=7,color='#8b3e18')
        for n,(x,y) in pos.items():ax.text(x,y,f'N{n}\nL{self.nodes[n]["line"]}',ha='center',va='center',fontsize=8,bbox=dict(boxstyle='round',fc='#eeedfa',ec='#5965be'))
        ax.set_xlim(-.4,2.4);ax.set_ylim(min(y for x,y in pos.values())-.6,.6);ax.axis('off');ax.set_title(f'{name}: N={len(ids)}, E={len(self.edges)}, P=1, V(G)={self.complexity}')
        fig.savefig(OUT/(base+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)
        # Independence is the rank of observed edge-parity vectors over GF(2).
        edge_list=[(a,b) for a,b,k in self.edges];basis={};rows=[]
        for trace in self.traces:
            counts=Counter(zip(trace['nodes'],trace['nodes'][1:]));vector=sum((counts[e]%2)<<i for i,e in enumerate(edge_list))
            reduced=vector
            while reduced:
                pivot=reduced.bit_length()-1
                if pivot not in basis: basis[pivot]=reduced;break
                reduced ^= basis[pivot]
            rows.append({'function':name,'case_id':trace['case_id'],'independent':bool(reduced),'path':'-'.join(map(str,trace['nodes'])),'input':trace['input'],'expected':json.dumps(trace['expected'],ensure_ascii=False),'actual':json.dumps(trace['actual'],ensure_ascii=False),'status':'PASSED' if trace['actual']==trace['expected'] else 'FAILED'})
        write(base+'_source.txt','\n'.join(f'{self.offset+i+1}: {line}' for i,line in enumerate(inspect.getsource(self.fn).splitlines())))
        return {'function':name,'nodes':len(ids),'edges':len(self.edges),'predicate_nodes':self.predicates,'P':1,'cyclomatic_complexity':self.complexity,'predicate_plus_one':self.predicates+1,'observed_independent_paths':len(basis),'basis_complete':len(basis)==self.complexity},rows
