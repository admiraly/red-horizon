#version 450 core
in vec3 colour;
in float distanceFog;
in vec3 surfaceAlbedo;
in vec3 surfaceNormal;
in vec3 surfacePosition;
flat in vec2 surfaceResponse;
uniform vec4 weather;
uniform vec3 camera;
uniform int meshMode;
layout(location=0) out vec4 outputColour;
flat in uint actorCode;
layout(location=1) out uint outputActorCode;
uniform int hdrOutput;
vec3 decodeDisplay(vec3 encoded){
 encoded=max(encoded,vec3(0));
 return mix(encoded/12.92,pow((encoded+.055)/1.055,vec3(2.4)),greaterThan(encoded,vec3(.04045)));
}
uniform int eventLightCount;
uniform vec4 eventLightPositions[8]; // XYZ and bounded influence radius
uniform vec4 eventLightColours[8]; // finite linear RGB energy
vec3 eventIrradiance(vec3 p,vec3 n){
 vec3 energy=vec3(0);
 for(int i=0;i<clamp(eventLightCount,0,8);++i){
  vec3 delta=eventLightPositions[i].xyz-p;
  float d2=dot(delta,delta),radius=max(eventLightPositions[i].w,.001);
  // Reject out-of-range/back-facing samples before square root and division.
  float facing=dot(n,delta);
  if(d2>=radius*radius||facing<=0.)continue;
  float edge=1.-d2/(radius*radius);
  float diffuse=facing*inversesqrt(max(d2,.0001));
  energy+=eventLightColours[i].rgb*(edge*edge*diffuse/(1.+d2*.05));
 }
 return energy;
}
uniform int sunShadowPass;
uniform int sunShadowReady;
uniform mat4 sunShadowMatrix;
layout(binding=14) uniform sampler2DShadow sunShadowMap;
float sunVisibility(vec3 p,vec3 n){
 if(sunShadowReady==0)return 1.;
 vec3 q=(sunShadowMatrix*vec4(p,1)).xyz;
 vec3 uv=q*.5+.5;
 // Receiver-plane depth correction keeps filtered coplanar terrain fully lit.
 vec3 dx=dFdx(uv),dy=dFdy(uv);
 float determinant=dx.x*dy.y-dx.y*dy.x;
 vec2 gradient=vec2(0);
 if(abs(determinant)>1e-20)
  gradient=clamp(vec2(dx.z*dy.y-dy.z*dx.y,dy.z*dx.x-dx.z*dy.x)/determinant,vec2(-4),vec2(4));
 if(any(greaterThanEqual(abs(q),vec3(1))))return 1.;
 float bias=max(.000025,.00015*(1.-max(0.,dot(n,normalize(vec3(.35,.85,-.2))))));
 // Account for the hardware comparison's half-texel footprint as well.
 bias+=dot(abs(gradient),vec2(.5/2048.));
 float visibility=0.;
 for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x){
  vec2 offset=vec2(x,y)/2048.;
  visibility+=texture(sunShadowMap,vec3(uv.xy+offset,uv.z+dot(gradient,offset)-bias));
 }
 float edge=smoothstep(.85,1.,max(abs(q.x),abs(q.y)));
 return mix(visibility/9.,1.,edge);
}
void main(){
 if(sunShadowPass!=0){outputColour=vec4(0);outputActorCode=0u;return;}
 outputActorCode=actorCode;
 vec3 surface=hdrOutput!=0?decodeDisplay(colour):colour;
 if(meshMode==0){
  vec3 n=normalize(surfaceNormal),sun=normalize(vec3(.35,.85,-.2));
  float clouds=clamp(weather.y,0.,1.),rain=clamp(weather.z,0.,1.);
  float direct=max(0.,dot(n,sun));
  if(hdrOutput!=0)direct*=sunVisibility(surfacePosition,n);
  vec3 ambient=mix(vec3(.55,.49,.42),vec3(.82,.91,1.),clamp(n.y*.5+.5,0.,1.));
  vec3 albedo=hdrOutput!=0?decodeDisplay(surfaceAlbedo):surfaceAlbedo;
  surface=albedo*(ambient*mix(.35,.58,clouds)+vec3(1.,.94,.82)*mix(.65,.22,clouds)*direct);
  if(hdrOutput!=0)surface+=albedo*eventIrradiance(surfacePosition,n);
  // Cloth/wrecks retain their matte response; rain coats intact equipment.
  float coating=surfaceResponse.y>.03?rain:0.;
  float roughness=mix(surfaceResponse.x,.22,coating);
  float gain=mix(surfaceResponse.y,.24,coating);
  vec3 eye=camera-surfacePosition;
  float eyeLength=length(eye);
  if(eyeLength>.0001){
   vec3 view=eye/eyeLength,halfway=view+sun;
   float halfLength=length(halfway);
   if(halfLength>.0001){
    float power=mix(128.,12.,roughness*roughness);
    float highlight=pow(max(0.,dot(n,halfway/halfLength)),power);
    surface+=vec3(1.,.94,.82)*highlight*gain*direct*(1.-clouds*.8)*max(0.,dot(n,view));
   }
  }
 }
 if(meshMode==2&&hdrOutput!=0)surface+=decodeDisplay(surfaceAlbedo)*eventIrradiance(surfacePosition,normalize(surfaceNormal));
 float fog=(meshMode==1||meshMode==2)?0.:1.-exp(-distanceFog*(.00018+weather.w));
 vec3 fogColour=mix(vec3(.49,.61,.68),vec3(.49,.53,.55),weather.y);
 if(hdrOutput!=0)fogColour=decodeDisplay(fogColour);
 outputColour=vec4(mix(surface,fogColour,fog),1);
}
