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
void main(){
 outputActorCode=actorCode;
 vec3 surface=hdrOutput!=0?decodeDisplay(colour):colour;
 if(meshMode==0){
  vec3 n=normalize(surfaceNormal),sun=normalize(vec3(.35,.85,-.2));
  float clouds=clamp(weather.y,0.,1.),rain=clamp(weather.z,0.,1.);
  float direct=max(0.,dot(n,sun));
  vec3 ambient=mix(vec3(.55,.49,.42),vec3(.82,.91,1.),clamp(n.y*.5+.5,0.,1.));
  vec3 albedo=hdrOutput!=0?decodeDisplay(surfaceAlbedo):surfaceAlbedo;
  surface=albedo*(ambient*mix(.35,.58,clouds)+vec3(1.,.94,.82)*mix(.65,.22,clouds)*direct);
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
 float fog=(meshMode==1||meshMode==2)?0.:1.-exp(-distanceFog*(.00018+weather.w));
 vec3 fogColour=mix(vec3(.49,.61,.68),vec3(.49,.53,.55),weather.y);
 if(hdrOutput!=0)fogColour=decodeDisplay(fogColour);
 outputColour=vec4(mix(surface,fogColour,fog),1);
}
