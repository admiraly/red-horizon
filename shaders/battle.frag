#version 450 core
in vec3 colour;
in float distanceFog;
in float effectAlpha;
in vec2 effectUV;
flat in int effectType;
in vec3 worldPosition;
flat in int materialMode;
uniform vec4 weather; // elapsed render time, cloud coverage, rain, fog density
uniform sampler2DArray terrainTextures;
uniform vec3 camera;
uniform vec2 angle;
uniform int commandWheelMode;
layout(location=0) out vec4 outputColour;
layout(location=1) out uint outputActorCode;
float noise(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float smoothNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(noise(i),noise(i+vec2(1,0)),f.x),mix(noise(i+vec2(0,1)),noise(i+vec2(1)),f.x),f.y);}
// Authored 5x7 command font, ASCII32..95; slot92 is pipe (normalized by NASM).
const uvec2 commandFont[64]=uvec2[64](
 uvec2(0u,0u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(2515893578u,2u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(1015808u,0u),
 uvec2(134217728u,1u),
 uvec2(1109533200u,0u),
 uvec2(2738546222u,3u),
 uvec2(2286031044u,3u),
 uvec2(3292807726u,7u),
 uvec2(3775349263u,3u),
 uvec2(301246856u,2u),
 uvec2(3775366207u,3u),
 uvec2(2736227374u,3u),
 uvec2(2216829471u,0u),
 uvec2(2736211502u,3u),
 uvec2(2702132782u,3u),
 uvec2(138416256u,0u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(1663026734u,4u),
 uvec2(3809986095u,3u),
 uvec2(2182120510u,7u),
 uvec2(3810051631u,3u),
 uvec2(3256321087u,7u),
 uvec2(1108837439u,0u),
 uvec2(2736686142u,7u),
 uvec2(1663026737u,4u),
 uvec2(3359772831u,7u),
 uvec2(2458132764u,1u),
 uvec2(1381078321u,4u),
 uvec2(3255862305u,7u),
 uvec2(1662703473u,4u),
 uvec2(1662834289u,4u),
 uvec2(2736309806u,3u),
 uvec2(1108854319u,0u),
 uvec2(2472068654u,5u),
 uvec2(1381484079u,4u),
 uvec2(3775333438u,3u),
 uvec2(138547359u,1u),
 uvec2(2736309809u,3u),
 uvec2(353945137u,1u),
 uvec2(2874852913u,2u),
 uvec2(1654794801u,4u),
 uvec2(138553905u,1u),
 uvec2(3257016863u,7u),
 uvec2(4473390u,1u),
 uvec2(138547332u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u),
 uvec2(4473390u,1u));
void main(){
 outputActorCode=0u;
 if(materialMode==13){
  float r=length(effectUV),radius=worldPosition.x;
  if(r>1.)discard;
  int sector=abs(effectUV.x)>abs(effectUV.y)?(effectUV.x<0.?1:3):(effectUV.y<0.?0:2);
  bool northeast=effectUV.x>0.&&effectUV.y<0.;
  if(northeast&&effectUV.x>=-.5*effectUV.y&&effectUV.x<=-2.*effectUV.y)sector=4;
  bool selected=r*radius>=38.&&sector==commandWheelMode;
  vec3 shade=selected?vec3(.12,.32,.25):vec3(.035,.06,.075);
  bool boundary=northeast?(abs(effectUV.x+.5*effectUV.y)<.012||abs(effectUV.x+2.*effectUV.y)<.012):abs(abs(effectUV.x)-abs(effectUV.y))<.012;
  if(r>.985||boundary)shade=vec3(.24,.45,.39);
  if(r*radius<38.)shade=vec3(.035,.06,.075);
  outputColour=vec4(shade,1);return;
 }
 if(materialMode==12){
  ivec2 cell=ivec2(floor(effectUV*vec2(6,8)));
  bool lit=false;
  if(cell.x>=0&&cell.x<5&&cell.y>=0&&cell.y<7){
   int bit=cell.y*5+cell.x;
   uvec2 mask=commandFont[clamp(effectType-32,0,63)];
   lit=((bit<32?mask.x:mask.y)>>uint(bit%32)&1u)!=0u;
  }
  outputColour=vec4(lit?vec3(.84,.94,.90):vec3(.035,.06,.075),1);
  return;
 }
 vec3 fogColour=mix(vec3(.49,.61,.68),vec3(.49,.53,.55),weather.y);
 if(materialMode==9){
  vec2 uv=effectUV;float elevation=clamp(uv.y*.5+.5+angle.y*.5,0.,1.);
  vec3 sky=mix(vec3(.65,.74,.77),vec3(.18,.40,.61),pow(elevation,.6));
  sky=mix(sky,mix(vec3(.53,.58,.60),vec3(.28,.34,.39),elevation),weather.y);
  vec2 cloudUV=vec2(uv.x+angle.x*.65,uv.y+angle.y)*vec2(4.,6.)+vec2(weather.x*.007,weather.x*.002);
  float cloud=smoothNoise(cloudUV)*.55+smoothNoise(cloudUV*2.3)*.30+smoothNoise(cloudUV*4.6)*.15;
  cloud=smoothstep(1.-weather.y*.78,1.-weather.y*.78+.16,cloud)*smoothstep(.12,.6,elevation);
  sky=mix(sky,mix(vec3(.92,.94,.94),vec3(.67,.70,.71),weather.y),cloud*.8);
  float sun=pow(max(0.,1.-length(uv-vec2(.45-angle.x*.6,.52-angle.y))),28.)*(1.-weather.y);
  outputColour=vec4(sky+vec3(1.,.78,.46)*sun*.18,1);return;
 }
 vec3 surface=colour;
 if(materialMode==1){
  vec2 p=worldPosition.xz,uv=p/3.5;
  vec3 grass=texture(terrainTextures,vec3(uv,0)).rgb;
  vec3 mud=texture(terrainTextures,vec3(uv*.8,1)).rgb;
  vec3 gravel=texture(terrainTextures,vec3(uv*1.1,2)).rgb;
  vec3 rock=texture(terrainTextures,vec3(uv*.7,3)).rgb;
  // Canonical capsules match the authoritative road sampler. The 2 m blend
  // outside the physical road is a visual shoulder, not road traction.
  float roadEdge=1e20;
  for(int i=0;i<terrainRoadCount;++i)
   if((terrainRoadFlags[i]&1u)!=0u)
    roadEdge=min(roadEdge,terrainRoadDistance(p,i)-terrainRoadHalfWidths[i]);
  float corridor=1.-smoothstep(0.,2.,roadEdge);
  float objective=1.-smoothstep(28.,75.,length(vec2(mod(p.x+0.,2000.)-1000.,mod(p.y+0.,2600.)-1300.)));
  float patchiness=smoothNoise(p/55.);
  vec3 n=normalize(cross(dFdy(worldPosition),dFdx(worldPosition)));if(n.y<0.)n=-n;
  float slope=1.-n.y;
  surface=mix(grass,mud,smoothstep(.45,.85,patchiness)*.45+weather.z*.16);
  surface=mix(surface,gravel,max(corridor*.72,objective*.8));
  surface=mix(surface,rock,clamp(slope*5.+smoothstep(.80,.98,patchiness)*.25,0.,1.));
  // Albedo-derived micro variation, not an authored normal map or PBR material.
  float grain=dot(surface,vec3(.333));n=normalize(n+vec3(dFdx(grain)*.4,0.,dFdy(grain)*.4));
  float light=mix(.35,.58,weather.y)+mix(.65,.22,weather.y)*max(0.,dot(n,normalize(vec3(.35,.85,-.2))));
  surface*=light*mix(1.,.67,weather.z);
  vec3 view=normalize(camera-worldPosition),halfway=normalize(view+normalize(vec3(.35,.85,-.2)));
  surface+=vec3(.16,.18,.19)*pow(max(0.,dot(n,halfway)),14.)*weather.z;
 }
 float alpha=effectAlpha;
 if(effectType>=2){
  vec2 uv=effectUV;float r=length(uv);if(r>1.)discard;
  if(effectType==3||effectType==5||effectType==7||effectType==8){
   float billow=smoothNoise(uv*5.+vec2(worldPosition.y*.09));
   alpha*=smoothstep(1.,.2,r)*mix(.5,1.,billow);
   surface*=mix(.72,1.2,billow);
  }else if(effectType==9){
   if(abs(uv.x)>.8||abs(uv.y)>.3||abs(uv.x*.4+uv.y)>.5)discard;
   alpha*=1.-smoothstep(.2,.95,r);
  }
  else if(effectType==4){alpha*=1.-smoothstep(.45,.95,r);}
  else{alpha*=smoothstep(1.,.35,r);}
 }
 // Screen UI and map symbols remain readable; emission effects retain their hue.
 float fog=1.-exp(-distanceFog*(.00018+weather.w));
 if(materialMode==2||materialMode==3||materialMode==4||materialMode==7||materialMode==8)fog=0.;
 outputColour=vec4(mix(surface,fogColour,fog),alpha);
}
