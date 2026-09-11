"""Shared, small proportion correction against approved hold identity."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
sys.path.insert(0,str(Path.home()/'.codex/skills/hatch-pet/scripts'))
from extract_strip_frames import connected_components
from despill_chroma_edges import decontaminate_image

def refine(im,side):
    a=np.array(im).astype(float);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(float)
    # Remove disconnected source motion dashes and antialias speckles only.
    seed=im.copy();alpha=np.array(seed)[:,:,3];alpha[alpha<24]=0;seed.putalpha(Image.fromarray(alpha))
    removed=[]
    for group in connected_components(seed):
        if group['area']<180:
            a.reshape(-1,4)[group['pixels']]=0;removed.append(int(group['area']))
    headscale=.90 if side=='left' else .89
    sx=np.interp(yy,[0,50,120,168,210,275,303,360],[headscale,headscale,headscale,.94,1,1,.94,.94])
    mx=260+(xx-260)/sx
    my=np.interp(yy,[0,50,110,165,205,280,294,330,360],[0,50,117,177,210,280,301,330,360])
    outer=np.clip((np.abs(xx-260)-90)/45,0,1);mx=mx*(1-outer)+xx*outer;my=my*(1-outer)+yy*outer
    mx=np.clip(mx,0,w-1);my=np.clip(my,0,h-1);x0=mx.astype(int);y0=my.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    fx=(mx-x0)[:,:,None];fy=(my-y0)[:,:,None];p=a.copy();p[:,:,:3]*=p[:,:,3:4]/255
    v=(p[y0,x0]*(1-fx)+p[y0,x1]*fx)*(1-fy)+(p[y1,x0]*(1-fx)+p[y1,x1]*fx)*fy
    v[:,:,:3]=np.divide(v[:,:,:3]*255,v[:,:,3:4],out=np.zeros_like(v[:,:,:3]),where=v[:,:,3:4]>0)
    v=np.clip(np.rint(v),0,255).astype('uint8');v[v[:,:,3]<16]=0;out=Image.fromarray(v)
    # Reduce only high-frequency feather texture, preserving silhouettes and
    # all eye/beak/hand edges. Texture in these generated reactions is stronger.
    sm=np.array(out.filter(ImageFilter.GaussianBlur(.65))).astype(float);rgb=v[:,:,:3].astype(float)
    lowcontrast=np.max(np.abs(rgb-sm[:,:,:3]),axis=2)<16
    interior=np.array(out.getchannel('A').filter(ImageFilter.MinFilter(5)))==255
    feather=(rgb[:,:,0]-rgb[:,:,1]<42)&(rgb[:,:,2]>45)&(xx>125)&(xx<390)
    use=lowcontrast&interior&feather
    rgb[use]=.55*rgb[use]+.45*sm[:,:,:3][use];v[:,:,:3]=np.rint(rgb).astype('uint8');out=Image.fromarray(v)
    out,edge=decontaminate_image(out,chroma_key=(255,0,255),edge_radius=5)
    return out,{'headHorizontalScale':headscale,'footHorizontalScale':.94,'verticalLandmarks':{'destination':[50,110,165,205,280,294,330],'source':[50,117,177,210,280,301,330]},'removedDisconnectedAreas':removed,'textureSoftenedPixels':int(use.sum()),'edgeCleanup':edge}
